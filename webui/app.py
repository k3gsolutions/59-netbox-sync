# Wrapper to import app from k3g-monitoring-iac/webui
import sys
from pathlib import Path
import importlib.util
import types

# Add the nested webui directory to sys.path
nested_webui_path = Path(__file__).parent.parent / "k3g-monitoring-iac" / "webui"
if str(nested_webui_path) not in sys.path:
    sys.path.insert(0, str(nested_webui_path))

# Create a fake package hierarchy so relative imports work
# First create the services "package" as a namespace
services_dir = nested_webui_path / "services"
if str(services_dir) not in sys.path:
    sys.path.insert(0, str(services_dir))

# Load app.py as a proper module with __package__ set
app_path = nested_webui_path / "app.py"
spec = importlib.util.spec_from_file_location("webui_nested", app_path)
webui_app = importlib.util.module_from_spec(spec)
webui_app.__package__ = "webui_nested"
webui_app.__file__ = str(app_path)

# Register in sys.modules BEFORE executing so relative imports can find the package
sys.modules["webui_nested"] = webui_app

# Register services as a submodule
services_package = types.ModuleType("webui_nested.services")
services_package.__path__ = [str(services_dir)]
services_package.__package__ = "webui_nested.services"
services_package.__file__ = str(services_dir / "__init__.py")
sys.modules["webui_nested.services"] = services_package

# Now load all service modules into the services package
for service_file in services_dir.glob("*.py"):
    if service_file.name.startswith("_"):
        continue
    module_name = service_file.stem
    spec = importlib.util.spec_from_file_location(
        f"webui_nested.services.{module_name}",
        service_file
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "webui_nested.services"
    sys.modules[f"webui_nested.services.{module_name}"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        pass  # Some modules may fail, that's OK

# Now execute the main app module
try:
    spec = importlib.util.spec_from_file_location("webui_nested", app_path)
    webui_app = importlib.util.module_from_spec(spec)
    webui_app.__package__ = "webui_nested"
    webui_app.__file__ = str(app_path)
    sys.modules["webui_nested"] = webui_app
    spec.loader.exec_module(webui_app)
    app = webui_app.app
except Exception as e:
    raise ImportError(f"Failed to load nested app: {e}") from e

__all__ = ["app"]
