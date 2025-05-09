from functools import total_ordering
from typing import Any, Dict

from dedocutils.data_structures import BBox


@total_ordering
class Location:
    def __init__(self, page_number: int, bbox: BBox, name: str = "", rotated_angle: float = 0.0) -> None:
        self.page_number = page_number
        self.bbox = bbox
        self.name = name
        # TODO put self.order (change LineWithLocation, PdfImageAttachment, ScanTable)
        self.rotated_angle = rotated_angle

    def shift(self, shift_x: int, shift_y: int) -> None:
        self.bbox.shift(shift_x, shift_y)

    def to_dict(self) -> Dict[str, Any]:
        from collections import OrderedDict

        res = OrderedDict()
        res["page_number"] = self.page_number
        res["bbox"] = self.bbox.to_dict()  # [x_begin, y_begin, width, height]
        res["name"] = self.name
        res["rotated_angle"] = self.rotated_angle
        return res

    def __eq__(self, other: "Location") -> bool:
        return (self.page_number, self.bbox.y_bottom_right) == (other.page_number, other.bbox.y_bottom_right)

    def __lt__(self, other: "Location") -> bool:
        return (self.page_number, self.bbox.y_bottom_right) < (other.page_number, other.bbox.y_bottom_right)
