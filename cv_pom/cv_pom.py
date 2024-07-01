from __future__ import annotations
import dataclasses
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
import numpy as np
from ultralytics import YOLO
import cv2 as cv
import easyocr
from ultralytics.engine.results import Results


@dataclass
class QueryValue:
    value: str
    case_sensitive: bool = True
    contains: bool = False


@dataclass
class Query:
    label: QueryValue | None = None
    text: QueryValue | None = None


@dataclass
class POMElement:
    id: str
    label: str
    coords_tl: tuple[int, int]
    coords_br: tuple[int, int]
    center: tuple[int, int]
    bounding_rect: tuple[int, int, int, int]
    confidence: float
    attrs: dict[str, Any]

    def as_dict(self):
        return dataclasses.asdict(self)


class POM:
    """CV POM (Page Object Model) class.

    Used to convert image source into POM and then query the elements.
    """

    def __init__(self, model_path: str | Path) -> None:
        self.model = YOLO(model_path)
        self.elements: list[POMElement] = []
        self.annotated_frame: np.ndarray = None
        self._reader = easyocr.Reader(['en'])

    def convert_to_cvpom(self, source, ocr_props=None) -> POM:
        """Convert image to CV POM.

        Args:
            source: Image source, supports same data types as YOLO "predict" method
            ocr_props: properties for OCR to read text. Defaults to None.

        Returns:
            POM: self
        """
        self.elements = []
        self.annotated_frame = None

        #  Object detection
        self.elements = self._object_detection(source)

        # Optical character recognition
        if ocr_props:
            ocr_props_comb = {'image': source, 'batch_size': 3, 'canvas_size': 1200, 'paragraph': False}
            for prop in ocr_props:
                ocr_props_comb[prop] = ocr_props[prop]
            ref_elements_txt = []  # [([Coordinates], Text)]
            output_txts = self._reader.readtext(**ocr_props_comb)
            for output_txt in output_txts:
                coordinates = [output_txt[0][0][0], output_txt[0][0][1], output_txt[0][2][0], output_txt[0][2][1]]
                ref_elements_txt.append([[int(x) for x in coordinates], output_txt[1]])
            # overlapping
            for i in range(len(self.elements)):
                output_overlap = self._find_overlapping_rects([
                    self.elements[i].coords_tl[0],
                    self.elements[i].coords_tl[1],
                    self.elements[i].coords_br[0],
                    self.elements[i].coords_br[1]], ref_elements_txt)
                final_text = ''
                for output_txt in output_overlap:
                    final_text += output_txt[1] + ' '
                self.elements[i].attrs['text'] = final_text[:-1]
            # non - overlapping
            ocr_elements = self._find_non_overlapping_rects(self.elements, ref_elements_txt)
            for ocr_element in ocr_elements:
                id_n = len(self.elements)
                ocr_element.id = str(id_n)
                self.annotated_frame = cv.rectangle(
                    self.annotated_frame,
                    pt1=ocr_element.coords_br,
                    pt2=ocr_element.coords_tl,
                    color=(0, 255, 0),
                    thickness=3,
                )
                x, y = ocr_element.coords_tl
                cv.putText(
                    self.annotated_frame, 'ocr_element', (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3
                )
                self.elements.append(ocr_element)

        return self

    def _object_detection(self, source) -> list[POMElement]:
        """Retrieves all the elements using Object Detection ML Algorithm.
        Args:
            source: Image
        Returns:
            list[POMElement]: List of elements
        """
        elements: list[POMElement] = []

        results: list[Results] = self.model.predict(source, verbose=False)

        for result in results:
            self.annotated_frame = result.plot()
            for i in range(len(result.boxes.data.tolist())):
                data = result.boxes.data.tolist()[i]
                xmin, ymin, xmax, ymax, confidence, class_id = data
                tl = (int(xmin), int(ymin))
                br = (int(xmax), int(ymax))

                element = POMElement(
                    id=str(i),
                    label=results[0].names[class_id],
                    coords_tl=tl,
                    coords_br=br,
                    center=(
                        (br[0] + tl[0]) // 2,
                        (br[1] + tl[1]) // 2,
                    ),
                    bounding_rect=cv.boundingRect(np.array([tl, br])),
                    confidence=confidence,
                    attrs={},
                )

                elements.append(element)

        return elements

    def get_elements(self, query_dict: dict | None = None) -> list[POMElement]:
        """Get elements using a query.

        Query examples:
        - select by exact label:                {"label": "my-label"}
        - select by label containing substring: {"label": {"value: "my-label", "contains": True}}
        - select by label not case sensitive:   {"label": {"value: "my-label", "case_sensitive": False}}
        - select by exact text:                 {"text": "my-text"}
        - select by exact label and text:       {"label": "my-label", "text": "my-text"}

        When not specified, "case_sensitive" defaults to True and "contains" defaults to False.

        Args:
            query_dict: Query dictionary. Pass None to select all elements. Defaults to None.

        Returns:
            list[POMElement]: List of elements
        """
        if query_dict is None:
            return self.elements

        filtered: list[POMElement] = []

        query = self._parse_query(query_dict)

        for element in self.elements:
            label = element.label
            if not self._check_query_value(label, query.label):
                continue

            if query.text is not None and "text" not in element.attrs:
                continue

            if "text" in element.attrs:
                text = element.attrs["text"]
                if not self._check_query_value(text, query.text):
                    continue

            filtered.append(element)

        return filtered

    def to_json(self, indent=None) -> str:
        return json.dumps([el.as_dict() for el in self.elements], indent=indent)

    def _check_query_value(self, value: str, query_val: QueryValue | None) -> bool:
        if query_val is None:
            return True

        expected = query_val.value
        if not query_val.case_sensitive:
            value = value.lower()
            expected = expected.lower()

        if query_val.contains:
            if expected not in value:
                return False
        else:
            if expected != value:
                return False

        return True

    def _parse_query(self, query_dict: dict) -> Query:
        """While the user can pass query as a dictionary,
        internally we want to work with concrete types.
        """
        query = Query()
        for [key, item] in query_dict.items():
            if isinstance(item, dict):
                if "value" not in item:
                    raise Exception("Query object doesn't have 'value' field")
                query_val = QueryValue(item["value"])
                if "case_sensitive" in item:
                    query_val.case_sensitive = bool(item["case_sensitive"])
                if "contains" in item:
                    query_val.contains = bool(item["contains"])
                setattr(query, key, query_val)
            else:
                setattr(query, key, QueryValue(item))

        return query

    def _do_rect_share_space(self, rect1, rect2) -> bool:
        """Check if rects share space by comparing their coordinates
        rect = [xmin, ymin, xmax, ymax]

        returns bool
        """
        return not (rect1[2] < rect2[0] or  # rect1 is to the left of rect2
                    rect1[0] > rect2[2] or  # rect1 is to the right of rect2
                    rect1[3] < rect2[1] or  # rect1 is above rect2
                    rect1[1] > rect2[3])

    def _find_overlapping_rects(self, rect1: list, sq_w_txt: list) -> list:
        """Example usage:
        rect1 = [4, 1, 6, 3]
        sq_w_txt = [[[7, 4, 9, 2], 'text1'], [[11, 8, 13, 6], [5, 2, 7, 1], 'text2']]
        _find_overlapping_rects(rects1, rects2)

        returns list
        """
        overlapping_rects = []

        for sq_txt in sq_w_txt:
            # Check for overlap in x-axis and y-axis
            if self._do_rect_share_space(rect1, sq_txt[0]):
                # Rectangles overlap, add to the result
                overlapping_rects.append(sq_txt)

        return overlapping_rects

    def _find_non_overlapping_rects(self, pom_els: list[POMElement], ocr_els: list) -> list[POMElement]:
        """It will find all those elements from OCR that does not overlap with the
        Yolo recognised elements

        Example usage:
        pom_els = [POMElement(...), ...]
        ocr_els = [[11, 8, 13, 6], [5, 2, 7, 1], 'text2']]
        _find_non_overlapping_rects(pom_els, ocr_els)

        returns list[POMElement]
        """
        non_overlapping_rects = []

        for ocr_el in ocr_els:
            is_overlapping = False
            for pom_el in pom_els:
                if self._do_rect_share_space(
                        [pom_el.coords_tl[0],
                         pom_el.coords_tl[1],
                         pom_el.coords_br[0],
                         pom_el.coords_br[1]], ocr_el[0]):
                    is_overlapping = True

            if not is_overlapping:
                element = POMElement(
                    id='',
                    label='ocr_element',
                    coords_tl=(ocr_el[0][0], ocr_el[0][1]),
                    coords_br=(ocr_el[0][2], ocr_el[0][3]),
                    center=(
                        (ocr_el[0][0] + ocr_el[0][2]) // 2,
                        (ocr_el[0][1] + ocr_el[0][3]) // 2,
                    ),
                    bounding_rect=(
                        cv.boundingRect(np.array([(ocr_el[0][0], ocr_el[0][1]), (ocr_el[0][2], ocr_el[0][3])]))
                    ),
                    confidence=1.0,
                    attrs={'text': ocr_el[1]},
                )
                non_overlapping_rects.append(element)

        return non_overlapping_rects
