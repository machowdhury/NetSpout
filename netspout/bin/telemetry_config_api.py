# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/telemetry_config_api.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Typed, secret-safe boundary used only by shared telemetry config POST."""
import inspect
from typing import Dict, List, Literal, Optional, Union

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, StrictStr, create_model

try:
    from .models import TelemetryTransportConfig
    from .transport_credential_updates import CredentialUpdateError, decode_transport_update
except ImportError:  # Flat packaged modules.
    from models import TelemetryTransportConfig
    from transport_credential_updates import CredentialUpdateError, decode_transport_update


class UpdateFields(BaseModel):
    if hasattr(BaseModel, 'model_fields'):
        model_config = {'extra': 'forbid'}
    else:
        class Config:
            extra = 'forbid'


def input_field(*, secret=False):
    options = dict(default_factory=lambda: None, repr=not secret)
    if secret:
        if hasattr(BaseModel, 'model_fields'):
            options['json_schema_extra'] = {'writeOnly': True}
        else:
            options['writeOnly'] = True
    return Field(**options)


class KeepCredential(UpdateFields):
    operation: Literal['keep']


class ClearCredential(UpdateFields):
    operation: Literal['clear']


class ReplaceStringCredential(UpdateFields):
    operation: Literal['replace']
    value: StrictStr = Field(repr=False, **(
        {'json_schema_extra': {'writeOnly': True}} if hasattr(BaseModel, 'model_fields')
        else {'writeOnly': True}))


class ReplaceHeaderCredential(UpdateFields):
    operation: Literal['replace']
    value: Dict[StrictStr, StrictStr] = Field(repr=False, **(
        {'json_schema_extra': {'writeOnly': True}} if hasattr(BaseModel, 'model_fields')
        else {'writeOnly': True}))


class CredentialOperations(UpdateFields):
    hec_token: Union[KeepCredential, ClearCredential, ReplaceStringCredential] = input_field(secret=True)
    otel_headers: Union[KeepCredential, ClearCredential, ReplaceHeaderCredential] = input_field(secret=True)
    native_snmp_community: Union[KeepCredential, ClearCredential, ReplaceStringCredential] = input_field(secret=True)


# Reuse public field types, never the runtime model's constructor, defaults,
# secret exclusions, or inheritance. Factories leave defaults undocumented and
# exclude_unset preserves omission; supplied null still follows the field type.
_fields = getattr(TelemetryTransportConfig, 'model_fields', None)
if _fields is None:
    _fields = TelemetryTransportConfig.__fields__
_request_fields = {
    name: (field.annotation if hasattr(BaseModel, 'model_fields') else field.outer_type_, input_field())
    for name, field in _fields.items()
    if name not in ('hec_token', 'otel_headers', 'native_snmp_community')
}
_request_fields.update({
    'endpoint': (Optional[StrictStr], input_field()),
    'index': (Optional[StrictStr], input_field()),
    'token': (StrictStr, input_field(secret=True)),
    'hec_token': (StrictStr, input_field(secret=True)),
    'otel_headers': (Union[Dict[StrictStr, StrictStr], StrictStr], input_field(secret=True)),
    'native_snmp_community': (StrictStr, input_field(secret=True)),
    'credential_updates': (CredentialOperations, input_field(secret=True)),
})
TelemetryConfigUpdate = create_model('TelemetryConfigUpdate', __base__=UpdateFields, **_request_fields)


class SafeValidationIssue(BaseModel):
    loc: List[str]
    type: str
    msg: str


class SafeValidationResponse(BaseModel):
    detail: List[SafeValidationIssue]


CONFIG_UPDATE_RESPONSES = {
    422: {'model': SafeValidationResponse, 'description': 'Invalid configuration; input values are omitted'},
    415: {'model': SafeValidationResponse, 'description': 'Explicit content type must be JSON'},
}


def invalid_update_error():
    return HTTPException(status_code=422, detail=[{
        'loc': ['body'], 'type': 'invalid_configuration',
        'msg': 'Invalid telemetry configuration update',
    }])


class TelemetryConfigRoute(APIRoute):
    def __init__(self, *args, **kwargs):
        # New FastAPI versions default to requiring Content-Type. This route
        # deliberately preserves the older missing-header JSON behavior.
        if 'strict_content_type' in inspect.signature(APIRoute).parameters:
            kwargs['strict_content_type'] = False
        super().__init__(*args, **kwargs)

    def get_route_handler(self):
        original = super().get_route_handler()

        async def guarded(request: Request):
            supplied = request.headers.get('content-type')
            if supplied is not None:
                media_type = supplied.split(';', 1)[0].strip().lower()
                subtype = media_type[len('application/'):] if media_type.startswith('application/') else ''
                if not (media_type == 'application/json' or
                        (len(subtype) > 5 and subtype.endswith('+json') and '/' not in subtype)):
                    raise HTTPException(status_code=415, detail=[{
                        'loc': ['header', 'content-type'], 'type': 'unsupported_media_type',
                        'msg': 'Content-Type must identify JSON',
                    }])
            try:
                decode_transport_update(await request.body())
            except CredentialUpdateError:
                raise HTTPException(status_code=422, detail=[{
                    'loc': ['body'], 'type': 'invalid_json',
                    'msg': 'Expected a JSON object with unique object keys',
                }]) from None
            try:
                return await original(request)
            except RequestValidationError:
                # Never forward errors(), input, context, body, supplied field
                # names, or arbitrary exception messages to the public response.
                raise invalid_update_error() from None

        return guarded
