from pathlib import Path

from mkdocs.structure.files import File


def on_files(files, config):
    """Publish the committed openapi.json"""
    spec = Path(config.config_file_path).parent / "openapi.json"
    files.append(File.generated(config, "openapi.json", abs_src_path=str(spec)))
    return files
