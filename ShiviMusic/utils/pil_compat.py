# Pillow 9.5.x crashes in ImageDraw.rounded_rectangle ("y1 must be greater than
# or equal to y0") when the box height/width is odd and the radius is just under
# half of it (e.g. a 57px-high pill with radius 28). This wrapper rounds such a
# radius up to a full "pill" so every Pillow version behaves the same.
from PIL import ImageDraw

if not getattr(ImageDraw.ImageDraw.rounded_rectangle, "_safe_radius", False):
    _orig_rounded_rectangle = ImageDraw.ImageDraw.rounded_rectangle

    def _safe_rounded_rectangle(self, xy, radius=0, *args, **kwargs):
        try:
            if isinstance(xy[0], (list, tuple)):
                (x0, y0), (x1, y1) = xy
            else:
                x0, y0, x1, y1 = xy
            m = min(x1 - x0, y1 - y0)
            if m - 2 < 2 * radius < m:
                radius = (m + 1) // 2
        except Exception:
            pass
        return _orig_rounded_rectangle(self, xy, radius, *args, **kwargs)

    _safe_rounded_rectangle._safe_radius = True
    ImageDraw.ImageDraw.rounded_rectangle = _safe_rounded_rectangle
