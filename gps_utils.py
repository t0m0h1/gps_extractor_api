from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_gps(filepath):
    image = Image.open(filepath)
    exif_data = image._getexif()
    if not exif_data:
        return None

    gps_info = {}
    for tag, value in exif_data.items():
        decoded = TAGS.get(tag)
        if decoded == "GPSInfo":
            for t in value:
                sub_decoded = GPSTAGS.get(t)
                gps_info[sub_decoded] = value[t]

    def convert_to_degrees(value):
        d, m, s = value
        return d[0] / d[1] + m[0] / m[1] / 60 + s[0] / s[1] / 3600

    if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
        lat = convert_to_degrees(gps_info["GPSLatitude"])
        if gps_info.get("GPSLatitudeRef") == "S":
            lat = -lat

        lon = convert_to_degrees(gps_info["GPSLongitude"])
        if gps_info.get("GPSLongitudeRef") == "W":
            lon = -lon

        altitude = gps_info.get("GPSAltitude", (0, 1))
        alt = altitude[0] / altitude[1] if altitude else None

        return {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "altitude": round(alt, 2) if alt is not None else None
        }

    return None
