"""
NetSpout Gate 13B — Native gNMI Server & gRPC Servicer Implementation.

Implements a real, standards-based, read-only gNMI (v0.10.0) target over:
  TCP -> HTTP/2 -> gRPC -> gNMI Protobuf

Supported RPCs:
  - Capabilities: returns gNMI 0.10.0, supported encodings (JSON, PROTO, JSON_IETF),
    and vendor-profile-aware supported_models.
  - Get: supports ALL, CONFIG, STATE, OPERATIONAL, prefix + multi-path, wildcards,
    JSON_IETF / JSON / PROTO encodings, and strict error handling.
  - Set: unconditionally disabled by security policy (returns StatusCode.UNIMPLEMENTED).
  - Subscribe: supports ONCE, POLL, STREAM / SAMPLE, and STREAM / ON_CHANGE with
    initial sync + sync_response=true, suppress_redundant, heartbeat_interval,
    500ms minimum sample interval floor, and slow-consumer backpressure protection.
"""

from concurrent import futures
from dataclasses import dataclass, field
import datetime
import ipaddress
import queue
import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import grpc

from .encoding import (
    GnmiEncodingError,
    GnmiUnsupportedEncodingError,
    validate_encoding,
)
from .path_parser import (
    GnmiPathParseError,
    ParsedGnmiPath,
    ParsedPathElem,
    parse_proto_path,
)
from .proto import gnmi_pb2, gnmi_pb2_grpc
from .sensor_registry import (
    GnmiForeignOriginError,
    GnmiPathNotFoundError,
    ResolvedSensorSample,
    TelemetrySensorRegistry,
)
from .state_store import DeviceStateSnapshot, ScenarioStateStore
from .subscription import (
    SubscriptionItemTracker,
    build_notification_from_sample,
    canonical_payload_fingerprint,
)
from .vendor_profiles import (
    GNMI_SEMVER,
    SUPPORTED_ENCODINGS,
    VendorProfile,
    get_vendor_profile,
)


@dataclass(frozen=True)
class EphemeralTlsMaterial:
    """In-memory X.509 certificate authority, server, and client key material for TLS/mTLS."""
    ca_cert_pem: bytes
    server_cert_pem: bytes
    server_key_pem: bytes
    client_cert_pem: bytes
    client_key_pem: bytes


def generate_ephemeral_tls_material() -> EphemeralTlsMaterial:
    """
    Generates ephemeral X.509 CA, server cert (for 127.0.0.1 / localhost), and client cert
    entirely in memory so no private keys are ever committed to the repository.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    valid_from = now - datetime.timedelta(minutes=5)
    valid_to = now + datetime.timedelta(days=7)

    # 1. Root CA
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NetSpout Ephemeral Lab CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, "NetSpout gNMI Test Root CA"),
        ]
    )
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_to)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    # 2. Server Certificate (SAN: 127.0.0.1, ::1, localhost, netspout-gnmi.local)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NetSpout Telemetry Target"),
            x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
        ]
    )
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_to)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("netspout-gnmi.local"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.IPAddress(ipaddress.ip_address("::1")),
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # 3. Client Certificate (for mTLS verification)
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NetSpout Telemetry Collector"),
            x509.NameAttribute(NameOID.COMMON_NAME, "netspout-gnmi-client"),
        ]
    )
    client_cert = (
        x509.CertificateBuilder()
        .subject_name(client_subject)
        .issuer_name(ca_subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_to)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    return EphemeralTlsMaterial(
        ca_cert_pem=ca_cert.public_bytes(serialization.Encoding.PEM),
        server_cert_pem=server_cert.public_bytes(serialization.Encoding.PEM),
        server_key_pem=server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        client_cert_pem=client_cert.public_bytes(serialization.Encoding.PEM),
        client_key_pem=client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )


@dataclass
class NativeGnmiServerConfig:
    """Configuration for the NetSpout Native gNMI Server."""
    bind_address: str = "127.0.0.1"
    bind_port: int = 57400
    allow_non_loopback: bool = False
    security_mode: str = "INSECURE_LOCAL_LAB"  # INSECURE_LOCAL_LAB | TLS_SERVER_AUTH | MTLS_CLIENT_AUTH
    require_metadata_auth: bool = False
    username: str = "netspout-lab"
    password: str = "netspout-lab-pass"
    default_target: str = "node-cisco8k"
    max_concurrent_connections: int = 16
    max_active_streams: int = 32
    max_paths_per_request: int = 64
    max_queue_size_per_stream: int = 256
    min_sample_interval_ns: int = 500_000_000  # 500ms floor
    default_sample_interval_ns: int = 5_000_000_000  # 5s default
    clamp_sample_interval: bool = False
    max_message_bytes: int = 4 * 1024 * 1024  # 4 MiB
    tls_ca_cert_pem: Optional[bytes] = None
    tls_server_cert_pem: Optional[bytes] = None
    tls_server_key_pem: Optional[bytes] = None

    def validate(self) -> None:
        loopback_hosts = {"127.0.0.1", "::1", "localhost"}
        if self.bind_address not in loopback_hosts and not self.allow_non_loopback:
            raise ValueError(
                f"NON_LOOPBACK_BIND_REJECTED: Cannot bind gNMI server to {self.bind_address!r} "
                "without explicit allow_non_loopback=True."
            )
        valid_modes = {"INSECURE_LOCAL_LAB", "TLS_SERVER_AUTH", "MTLS_CLIENT_AUTH"}
        if self.security_mode not in valid_modes:
            raise ValueError(f"Unsupported security_mode: {self.security_mode!r}")

    def to_redacted_dict(self) -> Dict[str, Any]:
        """Returns a safe dictionary representation with secrets and keys redacted."""
        return {
            "bind_address": self.bind_address,
            "bind_port": self.bind_port,
            "allow_non_loopback": self.allow_non_loopback,
            "security_mode": self.security_mode,
            "require_metadata_auth": self.require_metadata_auth,
            "username": self.username,
            "password": "***REDACTED***" if self.password else None,
            "default_target": self.default_target,
            "max_concurrent_connections": self.max_concurrent_connections,
            "max_active_streams": self.max_active_streams,
            "max_paths_per_request": self.max_paths_per_request,
            "max_queue_size_per_stream": self.max_queue_size_per_stream,
            "min_sample_interval_ns": self.min_sample_interval_ns,
            "default_sample_interval_ns": self.default_sample_interval_ns,
            "clamp_sample_interval": self.clamp_sample_interval,
            "max_message_bytes": self.max_message_bytes,
            "tls_configured": bool(self.tls_server_cert_pem and self.tls_server_key_pem),
            "tls_server_key_pem": "***REDACTED***" if self.tls_server_key_pem else None,
        }


@dataclass
class GnmiServerDiagnostics:
    """Thread-safe telemetry and error counters for the gNMI server."""
    capabilities_requests: int = 0
    get_requests: int = 0
    set_requests_rejected: int = 0
    subscribe_once_requests: int = 0
    subscribe_poll_requests: int = 0
    subscribe_stream_requests: int = 0
    active_streams: int = 0
    peak_active_streams: int = 0
    notifications_emitted: int = 0
    sync_responses_emitted: int = 0
    auth_failures: int = 0
    invalid_argument_errors: int = 0
    not_found_errors: int = 0
    unimplemented_errors: int = 0
    resource_exhausted_errors: int = 0
    clamped_sample_intervals: int = 0
    slow_consumer_drops: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, attr: str, delta: int = 1) -> None:
        with self._lock:
            current = getattr(self, attr)
            setattr(self, attr, current + delta)

    def stream_opened(self, max_active_streams: int) -> bool:
        with self._lock:
            if self.active_streams >= max_active_streams:
                self.resource_exhausted_errors += 1
                return False
            self.active_streams += 1
            if self.active_streams > self.peak_active_streams:
                self.peak_active_streams = self.active_streams
            return True

    def stream_closed(self) -> None:
        with self._lock:
            if self.active_streams > 0:
                self.active_streams -= 1

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return {
                "capabilities_requests": self.capabilities_requests,
                "get_requests": self.get_requests,
                "set_requests_rejected": self.set_requests_rejected,
                "subscribe_once_requests": self.subscribe_once_requests,
                "subscribe_poll_requests": self.subscribe_poll_requests,
                "subscribe_stream_requests": self.subscribe_stream_requests,
                "active_streams": self.active_streams,
                "peak_active_streams": self.peak_active_streams,
                "notifications_emitted": self.notifications_emitted,
                "sync_responses_emitted": self.sync_responses_emitted,
                "auth_failures": self.auth_failures,
                "invalid_argument_errors": self.invalid_argument_errors,
                "not_found_errors": self.not_found_errors,
                "unimplemented_errors": self.unimplemented_errors,
                "resource_exhausted_errors": self.resource_exhausted_errors,
                "clamped_sample_intervals": self.clamped_sample_intervals,
                "slow_consumer_drops": self.slow_consumer_drops,
            }


class NativeGnmiServicer(gnmi_pb2_grpc.gNMIServicer):
    """
    gRPC Servicer implementing the OpenConfig gNMI service:
      Capabilities, Get, Set (read-only disabled), and Subscribe.
    """

    def __init__(
        self,
        config: NativeGnmiServerConfig,
        state_store: ScenarioStateStore,
        sensor_registry: Optional[TelemetrySensorRegistry] = None,
        diagnostics: Optional[GnmiServerDiagnostics] = None,
    ) -> None:
        self.config = config
        self.state_store = state_store
        self.sensor_registry = sensor_registry or TelemetrySensorRegistry()
        self.diagnostics = diagnostics or GnmiServerDiagnostics()

    # ------------------------------------------------------------------
    # Authentication & Target Resolution Helpers
    # ------------------------------------------------------------------

    def _extract_metadata_dict(self, context: grpc.ServicerContext) -> Dict[str, str]:
        meta: Dict[str, str] = {}
        try:
            raw_meta = context.invocation_metadata()
            if raw_meta:
                for item in raw_meta:
                    key = str(item.key).lower()
                    val = item.value.decode("utf-8", errors="replace") if isinstance(item.value, bytes) else str(item.value)
                    meta[key] = val
        except Exception:
            pass
        return meta

    def _authenticate(self, context: grpc.ServicerContext) -> Dict[str, str]:
        meta = self._extract_metadata_dict(context)
        raw_user = meta.get("username", "").strip()
        raw_pw = meta.get("password", "").strip()
        has_creds_in_meta = (raw_user not in ("", "None")) or (raw_pw not in ("", "None"))

        if self.config.require_metadata_auth or has_creds_in_meta:
            if raw_user != self.config.username or raw_pw != self.config.password:
                self.diagnostics.inc("auth_failures")
                context.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    "UNAUTHENTICATED: Invalid or missing gNMI metadata credentials.",
                )
        return meta

    def _resolve_target_snapshot(
        self,
        explicit_target: str,
        meta: Dict[str, str],
        context: grpc.ServicerContext,
    ) -> DeviceStateSnapshot:
        candidate = (
            explicit_target.strip()
            or meta.get("x-netspout-target", "").strip()
            or meta.get("target", "").strip()
            or self.config.default_target
        )
        try:
            return self.state_store.get_snapshot(candidate)
        except KeyError:
            self.diagnostics.inc("not_found_errors")
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"UNKNOWN_TARGET: Target device {candidate!r} is not registered in ScenarioStateStore.",
            )
            raise RuntimeError("unreachable")

    # ------------------------------------------------------------------
    # 1. Capabilities RPC
    # ------------------------------------------------------------------

    def Capabilities(
        self,
        request: gnmi_pb2.CapabilitiesRequest,
        context: grpc.ServicerContext,
    ) -> gnmi_pb2.CapabilitiesResponse:
        meta = self._authenticate(context)
        self.diagnostics.inc("capabilities_requests")

        snap = self._resolve_target_snapshot("", meta, context)
        vprof = get_vendor_profile(snap.vendor_profile)

        resp = gnmi_pb2.CapabilitiesResponse(gNMI_version=GNMI_SEMVER)
        for enc_name in SUPPORTED_ENCODINGS:
            resp.supported_encodings.append( getattr(gnmi_pb2.Encoding, enc_name) )

        for mod in vprof.supported_models:
            resp.supported_models.append(
                gnmi_pb2.ModelData(
                    name=mod.name,
                    organization=mod.organization,
                    version=mod.version,
                )
            )
        return resp

    # ------------------------------------------------------------------
    # 2. Get RPC
    # ------------------------------------------------------------------

    def Get(
        self,
        request: gnmi_pb2.GetRequest,
        context: grpc.ServicerContext,
    ) -> gnmi_pb2.GetResponse:
        meta = self._authenticate(context)
        self.diagnostics.inc("get_requests")

        try:
            encoding = validate_encoding(request.encoding)
        except GnmiUnsupportedEncodingError as exc:
            self.diagnostics.inc("unimplemented_errors")
            context.abort(grpc.StatusCode.UNIMPLEMENTED, str(exc))
        except GnmiEncodingError as exc:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))

        if len(request.path) == 0 and (not request.HasField("prefix") or len(request.prefix.elem) == 0):
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "EMPTY_GET_PATHS: GetRequest must specify at least one path or non-empty prefix.",
            )

        if len(request.path) > self.config.max_paths_per_request:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"MAX_PATHS_EXCEEDED: GetRequest has {len(request.path)} paths (max {self.config.max_paths_per_request}).",
            )

        raw_prefix = request.prefix if request.HasField("prefix") else None
        try:
            parsed_prefix = parse_proto_path(raw_prefix) if raw_prefix is not None else None
        except GnmiPathParseError as exc:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            raise RuntimeError("unreachable")

        prefix_target = parsed_prefix.target if parsed_prefix else ""
        prefix_elems = parsed_prefix.elems if parsed_prefix else ()
        data_type_name = gnmi_pb2.GetRequest.DataType.Name(request.type)

        notifications: List[gnmi_pb2.Notification] = []
        raw_paths = list(request.path) if len(request.path) > 0 else [gnmi_pb2.Path()]

        for raw_p in raw_paths:
            try:
                parsed_path = parse_proto_path(raw_p, prefix=raw_prefix)
            except GnmiPathParseError as exc:
                self.diagnostics.inc("invalid_argument_errors")
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
                raise RuntimeError("unreachable")

            snap = self._resolve_target_snapshot(parsed_path.target or prefix_target, meta, context)

            try:
                samples = self.sensor_registry.resolve(
                    snap=snap,
                    path=parsed_path,
                    data_type=data_type_name,
                )
            except (GnmiPathNotFoundError, GnmiForeignOriginError) as exc:
                self.diagnostics.inc("not_found_errors")
                context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
                raise RuntimeError("unreachable")

            for sample in samples:
                notif = build_notification_from_sample(
                    sample=sample,
                    timestamp_ns=snap.timestamp_ns,
                    encoding=encoding,
                    request_prefix_elems=prefix_elems,
                )
                notifications.append(notif)
                self.diagnostics.inc("notifications_emitted")

        return gnmi_pb2.GetResponse(notification=notifications)

    # ------------------------------------------------------------------
    # 3. Set RPC (Unconditionally Disabled — Read-Only Security Policy)
    # ------------------------------------------------------------------

    def Set(
        self,
        request: gnmi_pb2.SetRequest,
        context: grpc.ServicerContext,
    ) -> gnmi_pb2.SetResponse:
        self._authenticate(context)
        self.diagnostics.inc("set_requests_rejected")
        self.diagnostics.inc("unimplemented_errors")
        context.abort(
            grpc.StatusCode.UNIMPLEMENTED,
            "NetSpout gNMI target is read-only; Set RPC is disabled by security policy.",
        )
        raise RuntimeError("unreachable")

    # ------------------------------------------------------------------
    # 4. Subscribe RPC (ONCE, POLL, STREAM/SAMPLE, STREAM/ON_CHANGE)
    # ------------------------------------------------------------------

    def Subscribe(
        self,
        request_iterator: Iterator[gnmi_pb2.SubscribeRequest],
        context: grpc.ServicerContext,
    ) -> Iterator[gnmi_pb2.SubscribeResponse]:
        meta = self._authenticate(context)

        try:
            first_req = next(request_iterator)
        except StopIteration:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "EMPTY_SUBSCRIBE_STREAM: Client closed stream before sending SubscriptionList.",
            )
            return

        if not first_req.HasField("subscribe"):
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "FIRST_SUBSCRIBE_MESSAGE_MUST_CONTAIN_SUBSCRIPTION_LIST: Initial message must contain 'subscribe'.",
            )
            return

        sub_list = first_req.subscribe

        try:
            encoding = validate_encoding(sub_list.encoding)
        except GnmiUnsupportedEncodingError as exc:
            self.diagnostics.inc("unimplemented_errors")
            context.abort(grpc.StatusCode.UNIMPLEMENTED, str(exc))
            return
        except GnmiEncodingError as exc:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            return

        if len(sub_list.subscription) == 0:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "EMPTY_SUBSCRIPTION_LIST: SubscriptionList must contain at least one Subscription.",
            )
            return

        if len(sub_list.subscription) > self.config.max_paths_per_request:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"MAX_PATHS_EXCEEDED: SubscriptionList has {len(sub_list.subscription)} subscriptions "
                f"(max {self.config.max_paths_per_request}).",
            )
            return

        raw_sub_prefix = sub_list.prefix if sub_list.HasField("prefix") else None
        try:
            parsed_prefix = parse_proto_path(raw_sub_prefix) if raw_sub_prefix is not None else None
        except GnmiPathParseError as exc:
            self.diagnostics.inc("invalid_argument_errors")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
            return

        prefix_target = parsed_prefix.target if parsed_prefix else ""
        prefix_elems = parsed_prefix.elems if parsed_prefix else ()
        snap = self._resolve_target_snapshot(prefix_target, meta, context)

        # Parse and pre-validate all subscription items
        trackers: List[SubscriptionItemTracker] = []
        initial_samples_per_tracker: List[List[ResolvedSensorSample]] = []

        for sub in sub_list.subscription:
            try:
                parsed_path = parse_proto_path(sub.path, prefix=raw_sub_prefix)
            except GnmiPathParseError as exc:
                self.diagnostics.inc("invalid_argument_errors")
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
                return

            try:
                resolved = self.sensor_registry.resolve(snap=snap, path=parsed_path, data_type="ALL")
            except (GnmiPathNotFoundError, GnmiForeignOriginError) as exc:
                self.diagnostics.inc("not_found_errors")
                context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
                return

            # Determine subscription mode (SAMPLE vs ON_CHANGE) for STREAM mode
            sub_mode = sub.mode
            if sub_mode == gnmi_pb2.TARGET_DEFINED:
                # Default to SAMPLE for counters, ON_CHANGE for state if unspecified
                sub_mode = gnmi_pb2.SAMPLE

            sample_interval_ns = int(sub.sample_interval)
            if sub_list.mode == gnmi_pb2.SubscriptionList.STREAM and sub_mode == gnmi_pb2.SAMPLE:
                if sample_interval_ns == 0:
                    sample_interval_ns = self.config.default_sample_interval_ns
                elif sample_interval_ns < self.config.min_sample_interval_ns:
                    if self.config.clamp_sample_interval:
                        sample_interval_ns = self.config.min_sample_interval_ns
                        self.diagnostics.inc("clamped_sample_intervals")
                    else:
                        self.diagnostics.inc("invalid_argument_errors")
                        context.abort(
                            grpc.StatusCode.INVALID_ARGUMENT,
                            f"SAMPLE_INTERVAL_BELOW_FLOOR: Requested sample_interval={sample_interval_ns}ns "
                            f"is below minimum floor {self.config.min_sample_interval_ns}ns (500ms).",
                        )
                        return

            tracker = SubscriptionItemTracker(
                parsed_path=parsed_path,
                request_prefix_elems=prefix_elems,
                mode=sub_mode,
                sample_interval_ns=sample_interval_ns,
                suppress_redundant=bool(sub.suppress_redundant),
                heartbeat_interval_ns=int(sub.heartbeat_interval),
            )
            trackers.append(tracker)
            initial_samples_per_tracker.append(resolved)

        # ------------------------------------------------------------------
        # Mode A: ONCE
        # ------------------------------------------------------------------
        if sub_list.mode == gnmi_pb2.SubscriptionList.ONCE:
            self.diagnostics.inc("subscribe_once_requests")
            if not sub_list.updates_only:
                for tracker, samples in zip(trackers, initial_samples_per_tracker):
                    for sample in samples:
                        notif = build_notification_from_sample(
                            sample=sample,
                            timestamp_ns=snap.timestamp_ns,
                            encoding=encoding,
                            request_prefix_elems=tracker.request_prefix_elems,
                        )
                        self.diagnostics.inc("notifications_emitted")
                        yield gnmi_pb2.SubscribeResponse(update=notif)

            self.diagnostics.inc("sync_responses_emitted")
            yield gnmi_pb2.SubscribeResponse(sync_response=True)
            return

        # ------------------------------------------------------------------
        # Mode B: POLL
        # ------------------------------------------------------------------
        if sub_list.mode == gnmi_pb2.SubscriptionList.POLL:
            self.diagnostics.inc("subscribe_poll_requests")
            # Emit initial snapshot + sync_response on subscription establishment
            if not sub_list.updates_only:
                for tracker, samples in zip(trackers, initial_samples_per_tracker):
                    for sample in samples:
                        notif = build_notification_from_sample(
                            sample=sample,
                            timestamp_ns=snap.timestamp_ns,
                            encoding=encoding,
                            request_prefix_elems=tracker.request_prefix_elems,
                        )
                        self.diagnostics.inc("notifications_emitted")
                        yield gnmi_pb2.SubscribeResponse(update=notif)

            self.diagnostics.inc("sync_responses_emitted")
            yield gnmi_pb2.SubscribeResponse(sync_response=True)

            # Wait for client Poll messages
            for next_req in request_iterator:
                if not context.is_active():
                    break
                if not next_req.HasField("poll"):
                    self.diagnostics.inc("invalid_argument_errors")
                    context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "EXPECTED_POLL_REQUEST_IN_POLL_MODE: Subsequent messages in POLL mode must set 'poll'.",
                    )
                    return

                poll_snap = self.state_store.get_snapshot(snap.device_id)
                for tracker in trackers:
                    poll_samples = self.sensor_registry.resolve(
                        snap=poll_snap, path=tracker.parsed_path, data_type="ALL"
                    )
                    for sample in poll_samples:
                        notif = build_notification_from_sample(
                            sample=sample,
                            timestamp_ns=poll_snap.timestamp_ns,
                            encoding=encoding,
                            request_prefix_elems=tracker.request_prefix_elems,
                        )
                        self.diagnostics.inc("notifications_emitted")
                        yield gnmi_pb2.SubscribeResponse(update=notif)

                self.diagnostics.inc("sync_responses_emitted")
                yield gnmi_pb2.SubscribeResponse(sync_response=True)
            return

        # ------------------------------------------------------------------
        # Mode C: STREAM (SAMPLE & ON_CHANGE)
        # ------------------------------------------------------------------
        if sub_list.mode == gnmi_pb2.SubscriptionList.STREAM:
            self.diagnostics.inc("subscribe_stream_requests")
            if not self.diagnostics.stream_opened(self.config.max_active_streams):
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"MAX_ACTIVE_STREAMS_EXCEEDED: Active streams limit ({self.config.max_active_streams}) reached.",
                )
                return

            out_queue: "queue.Queue[Optional[gnmi_pb2.SubscribeResponse]]" = queue.Queue(
                maxsize=self.config.max_queue_size_per_stream
            )
            overflow_event = threading.Event()
            stop_event = threading.Event()
            target_device_id = snap.device_id

            def _enqueue(resp: gnmi_pb2.SubscribeResponse) -> bool:
                try:
                    out_queue.put_nowait(resp)
                    return True
                except queue.Full:
                    overflow_event.set()
                    stop_event.set()
                    self.diagnostics.inc("slow_consumer_drops")
                    self.diagnostics.inc("resource_exhausted_errors")
                    return False

            # 1. Enqueue initial synchronization snapshot + sync_response=True
            now_ns = time.time_ns()
            for tracker, samples in zip(trackers, initial_samples_per_tracker):
                for sample in samples:
                    fp = canonical_payload_fingerprint(sample.payload)
                    c_xpath = sample.concrete_path.canonical_xpath
                    tracker.last_fingerprints[c_xpath] = fp
                    tracker.last_emit_time_ns[c_xpath] = now_ns
                    if not sub_list.updates_only:
                        notif = build_notification_from_sample(
                            sample=sample,
                            timestamp_ns=snap.timestamp_ns,
                            encoding=encoding,
                            request_prefix_elems=tracker.request_prefix_elems,
                        )
                        self.diagnostics.inc("notifications_emitted")
                        if not _enqueue(gnmi_pb2.SubscribeResponse(update=notif)):
                            break
                tracker.next_sample_due_ns = now_ns + tracker.sample_interval_ns

            self.diagnostics.inc("sync_responses_emitted")
            _enqueue(gnmi_pb2.SubscribeResponse(sync_response=True))

            # 2. Register ON_CHANGE listener on ScenarioStateStore
            tracker_lock = threading.Lock()

            def _on_phase_transition(
                _new_phase: str,
                _new_tick: int,
            ) -> None:
                if stop_event.is_set() or not context.is_active():
                    return
                try:
                    dev_snap = self.state_store.get_snapshot(target_device_id)
                except Exception:
                    return
                event_now_ns = time.time_ns()
                with tracker_lock:
                    for tracker in trackers:
                        if tracker.mode != gnmi_pb2.ON_CHANGE:
                            continue
                        try:
                            samples = self.sensor_registry.resolve(
                                snap=dev_snap, path=tracker.parsed_path, data_type="ALL"
                            )
                        except Exception:
                            continue
                        for sample in samples:
                            c_xpath = sample.concrete_path.canonical_xpath
                            fp = canonical_payload_fingerprint(sample.payload)
                            if tracker.should_emit_on_change(
                                c_xpath, fp, event_now_ns, is_heartbeat_check=False
                            ):
                                notif = build_notification_from_sample(
                                    sample=sample,
                                    timestamp_ns=dev_snap.timestamp_ns,
                                    encoding=encoding,
                                    request_prefix_elems=tracker.request_prefix_elems,
                                )
                                self.diagnostics.inc("notifications_emitted")
                                if not _enqueue(gnmi_pb2.SubscribeResponse(update=notif)):
                                    return

            self.state_store.register_listener(_on_phase_transition)

            # 3. Start background ticker thread for SAMPLE subscriptions and ON_CHANGE heartbeats
            def _stream_ticker() -> None:
                while not stop_event.is_set() and context.is_active():
                    time.sleep(0.05)
                    if stop_event.is_set() or not context.is_active():
                        break
                    tick_now_ns = time.time_ns()
                    with tracker_lock:
                        for tracker in trackers:
                            if tracker.mode == gnmi_pb2.SAMPLE:
                                if tick_now_ns >= tracker.next_sample_due_ns:
                                    tracker.next_sample_due_ns = tick_now_ns + tracker.sample_interval_ns
                                    # Advance monotonic counters slightly on each sample cadence
                                    self.state_store.advance_tick(1)
                                    live_snap = self.state_store.get_snapshot(target_device_id)
                                    try:
                                        samples = self.sensor_registry.resolve(
                                            snap=live_snap, path=tracker.parsed_path, data_type="ALL"
                                        )
                                    except Exception:
                                        continue
                                    for sample in samples:
                                        c_xpath = sample.concrete_path.canonical_xpath
                                        fp = canonical_payload_fingerprint(sample.payload)
                                        if tracker.should_emit_sample(c_xpath, fp, tick_now_ns):
                                            notif = build_notification_from_sample(
                                                sample=sample,
                                                timestamp_ns=live_snap.timestamp_ns,
                                                encoding=encoding,
                                                request_prefix_elems=tracker.request_prefix_elems,
                                            )
                                            self.diagnostics.inc("notifications_emitted")
                                            if not _enqueue(gnmi_pb2.SubscribeResponse(update=notif)):
                                                return
                            elif tracker.mode == gnmi_pb2.ON_CHANGE and tracker.heartbeat_interval_ns > 0:
                                live_snap = self.state_store.get_snapshot(target_device_id)
                                try:
                                    samples = self.sensor_registry.resolve(
                                        snap=live_snap, path=tracker.parsed_path, data_type="ALL"
                                    )
                                except Exception:
                                    continue
                                for sample in samples:
                                    c_xpath = sample.concrete_path.canonical_xpath
                                    fp = canonical_payload_fingerprint(sample.payload)
                                    if tracker.should_emit_on_change(
                                        c_xpath, fp, tick_now_ns, is_heartbeat_check=True
                                    ):
                                        notif = build_notification_from_sample(
                                            sample=sample,
                                            timestamp_ns=live_snap.timestamp_ns,
                                            encoding=encoding,
                                            request_prefix_elems=tracker.request_prefix_elems,
                                        )
                                        self.diagnostics.inc("notifications_emitted")
                                        if not _enqueue(gnmi_pb2.SubscribeResponse(update=notif)):
                                            return

            ticker_thread = threading.Thread(target=_stream_ticker, daemon=True)
            ticker_thread.start()

            def _on_rpc_done() -> None:
                stop_event.set()
                try:
                    out_queue.put_nowait(None)
                except queue.Full:
                    pass

            context.add_callback(_on_rpc_done)

            try:
                while context.is_active():
                    if overflow_event.is_set():
                        context.abort(
                            grpc.StatusCode.RESOURCE_EXHAUSTED,
                            "STREAM_QUEUE_OVERFLOW: Slow consumer exceeded max_queue_size_per_stream.",
                        )
                        return
                    try:
                        item = out_queue.get(timeout=0.1)
                    except queue.Empty:
                        if stop_event.is_set():
                            break
                        continue
                    if item is None:
                        break
                    yield item
                if overflow_event.is_set():
                    context.abort(
                        grpc.StatusCode.RESOURCE_EXHAUSTED,
                        "STREAM_QUEUE_OVERFLOW: Slow consumer exceeded max_queue_size_per_stream.",
                    )
            finally:
                stop_event.set()
                self.state_store.unregister_listener(_on_phase_transition)
                self.diagnostics.stream_closed()
            return


class NativeGnmiServer:
    """
    Lifecycle wrapper for the NetSpout Native gNMI gRPC server over TCP/HTTP2.
    """

    def __init__(
        self,
        config: Optional[NativeGnmiServerConfig] = None,
        state_store: Optional[ScenarioStateStore] = None,
        sensor_registry: Optional[TelemetrySensorRegistry] = None,
    ) -> None:
        self.config = config or NativeGnmiServerConfig()
        self.config.validate()
        self.state_store = state_store or ScenarioStateStore()
        self.sensor_registry = sensor_registry or TelemetrySensorRegistry()
        self.diagnostics = GnmiServerDiagnostics()
        self.servicer = NativeGnmiServicer(
            config=self.config,
            state_store=self.state_store,
            sensor_registry=self.sensor_registry,
            diagnostics=self.diagnostics,
        )
        self._server: Optional[grpc.Server] = None
        self._bound_port: int = self.config.bind_port

    @property
    def bound_port(self) -> int:
        return self._bound_port

    @property
    def endpoint(self) -> str:
        return f"{self.config.bind_address}:{self._bound_port}"

    def start(self) -> int:
        if self._server is not None:
            return self._bound_port

        options = [
            ("grpc.max_send_message_length", self.config.max_message_bytes),
            ("grpc.max_receive_message_length", self.config.max_message_bytes),
            ("grpc.max_concurrent_streams", max(128, self.config.max_active_streams * 2)),
            ("grpc.so_reuseport", 0),
        ]
        # Note: max_workers needs enough threads to service concurrent streaming RPCs + unary RPCs
        worker_threads = max(48, self.config.max_active_streams + 16)
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=worker_threads),
            options=options,
            maximum_concurrent_rpcs=self.config.max_concurrent_connections * 4,
        )
        gnmi_pb2_grpc.add_gNMIServicer_to_server(self.servicer, self._server)

        bind_target = f"{self.config.bind_address}:{self.config.bind_port}"
        if self.config.security_mode == "INSECURE_LOCAL_LAB":
            bound = self._server.add_insecure_port(bind_target)
        elif self.config.security_mode in ("TLS_SERVER_AUTH", "MTLS_CLIENT_AUTH"):
            if not self.config.tls_server_cert_pem or not self.config.tls_server_key_pem:
                raise ValueError(
                    f"TLS server certificate and key are required for security_mode={self.config.security_mode!r}"
                )
            require_client_auth = self.config.security_mode == "MTLS_CLIENT_AUTH"
            server_creds = grpc.ssl_server_credentials(
                [(self.config.tls_server_key_pem, self.config.tls_server_cert_pem)],
                root_certificates=self.config.tls_ca_cert_pem if require_client_auth else None,
                require_client_auth=require_client_auth,
            )
            bound = self._server.add_secure_port(bind_target, server_creds)
        else:
            raise ValueError(f"Unsupported security_mode: {self.config.security_mode!r}")

        if bound == 0:
            raise RuntimeError(f"Failed to bind gNMI gRPC server on {bind_target}")

        self._bound_port = bound
        self._server.start()
        return self._bound_port

    def stop(self, grace: Optional[float] = 0.5) -> None:
        if self._server is not None:
            self._server.stop(grace)
            self._server = None

    def status_summary(self) -> Dict[str, Any]:
        return {
            "running": self._server is not None,
            "endpoint": self.endpoint,
            "gNMI_version": GNMI_SEMVER,
            "scenario_phase": self.state_store.phase,
            "config": self.config.to_redacted_dict(),
            "diagnostics": self.diagnostics.snapshot(),
        }
