import sys, ssl, platform, importlib
print(sys.version.split()[0], ssl.OPENSSL_VERSION, platform.machine())
for m in ("grpc", "google.protobuf", "cryptography", "yaml", "pydantic_core"):
    try:
        mod = importlib.import_module(m); print(m, getattr(mod, "__version__", "ok"))
    except Exception as e:
        print(m, "MISSING", type(e).__name__)
