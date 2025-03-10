def skip_member(app, what, name, obj, skip, options):
    # Only document members explicitly listed in __all__
    public_api = getattr(app.config, "public_api", [])
    if name not in public_api:
        return True  # skip this member
    return skip

def setup(app):
    app.add_config_value("public_api", [], "env")
    app.connect("autodoc-skip-member", skip_member)

public_api = ["Maoto"]