"""Assign distinct family and PostScript names to the release and lab builds."""



def set_identity(font, family):
    prefix = family.replace(" ", "")
    postscript = prefix + "-Thin"
    names = font["name"]
    values = {
        1: family + " Thin",
        3: "4.000;NONE;" + postscript,
        4: family + " Thin",
        5: "Version 4.000",
        6: postscript,
        16: family,
        25: prefix,
    }
    platforms = {(r.platformID, r.platEncID, r.langID) for r in names.names if r.nameID == 1}
    for platform in platforms:
        for name_id, value in values.items():
            names.setName(value, name_id, *platform)
    font["head"].fontRevision = 4.0
