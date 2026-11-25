"""Assign distinct family and PostScript names to the release and lab builds."""



def set_identity(font, family, version="4.001"):
    prefix = family.replace(" ", "")
    postscript = prefix + "-Thin"
    names = font["name"]
    values = {
        1: family + " Thin",
        3: f"{version};NONE;{postscript}",
        4: family + " Thin",
        5: f"Version {version}",
        6: postscript,
        16: family,
        25: prefix,
    }
    platforms = {(r.platformID, r.platEncID, r.langID) for r in names.names if r.nameID == 1}
    for platform in platforms:
        for name_id, value in values.items():
            names.setName(value, name_id, *platform)
    font["head"].fontRevision = float(version)
