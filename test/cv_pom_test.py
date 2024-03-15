import base64
from pathlib import Path
import unittest
import json
import cv2 as cv
from fastapi.testclient import TestClient
from server import app
from cv_pom.cv_pom import POM, POMElement


class TestCVPOMConvert(unittest.TestCase):

    def setUp(self) -> None:
        self.pom = POM("yolov8n.pt")
        self.image_path = "test/resources/yolo_test_1.png"

    def test_image_path_to_pom(self):
        self.pom.convert_to_cvpom(self.image_path, True)
        elements = self.pom.get_elements()

        self.assertTrue(len(elements) > 0)

    def test_image_to_pom(self):
        self.pom.convert_to_cvpom(self.image_path, False)
        elements = self.pom.get_elements()

        self.assertTrue(len(elements) > 0)


def create_elements(pom_json: Path) -> list[POMElement]:
    """Test utility function that creates elements from
    JSON in order not to waste time on prediction"""
    with open(pom_json, "r") as f:
        data = json.load(f)

    elements = []
    for el in data:
        elements.append(
            POMElement(
                id=el["id"],
                attrs=el["attrs"],
                bounding_rect=el["bounding_rect"],
                center=el["center"],
                confidence=el["confidence"],
                coords_br=el["coords_br"],
                coords_tl=el["coords_tl"],
                label=el["label"],
            )
        )

    return elements


class TestCVPOMUtils(unittest.TestCase):
    def setUp(self) -> None:
        self.pom = POM("yolov8n.pt")
        # Artificially create elements
        self.pom.elements = create_elements("test/resources/pom_example.json")

    def test_overlap_rects(self):
        # TRUE
        list_rect1 = [[133, 27, 1469, 315], [151, 29, 1469, 315]]
        list_rect2 = [[1469, 315, 1471, 320]]
        for rect1 in list_rect1:
            for rect2 in list_rect2:
                self.assertTrue(
                    self.pom._do_rect_share_space(rect1, rect2),
                    f'The squares {rect1}, {rect2} should overlap, but did not'
                )

        # FALSE
        list_rect1 = [[133, 27, 1469, 315], [151, 321, 1469, 330]]
        list_rect2 = [[1470, 316, 1472, 320]]
        for rect1 in list_rect1:
            for rect2 in list_rect2:
                self.assertFalse(
                    self.pom._do_rect_share_space(rect1, rect2),
                    f'The squares {rect1}, {rect2} should not overlap, but did'
                )

    def test_find_overlapping_rects(self):
        rect1 = [4, 1, 8, 3]
        sq_w_txt = [[[7, 2, 9, 4], 'text1'], [[11, 8, 13, 6], [5, 2, 7, 1], 'text2']]
        result_exp = [[[7, 2, 9, 4], 'text1']]
        result = self.pom._find_overlapping_rects(rect1, sq_w_txt)
        self.assertEqual(result_exp, result, f'expecting found: {result_exp}, got {result}')

    def test_non_overlapping_rects(self):
        sq_w_txt = [[[2, 1, 3, 1], 'text1']]
        result_exp = [POMElement(
            id='',
            attrs={'text': 'text1'},
            bounding_rect=(2, 1, 2, 1),
            center=(2, 1),
            confidence=1.0,
            coords_br=(3, 1),
            coords_tl=(2, 1),
            label='ocr_element',
        )]
        result = self.pom._find_non_overlapping_rects(self.pom.elements, sq_w_txt)
        self.assertEqual(result_exp, result, f'expecting found: {result_exp}, got {result}')


class TestCVPOMQuery(unittest.TestCase):
    def setUp(self) -> None:
        self.pom = POM("yolov8n.pt")
        # Artificially create elements
        self.pom.elements = create_elements("test/resources/pom_example.json")

    def test_query_by_label(self):
        elements = self.pom.get_elements({"label": "text-btn"})

        self.assertTrue(len(elements) > 0)
        for el in elements:
            self.assertEqual(el.label, "text-btn")

    def test_query_by_text(self):
        elements = self.pom.get_elements({"text": {"value": "Your business", "contains": True}})

        self.assertTrue(len(elements) > 0)
        for el in elements:
            self.assertTrue("Your business" in el.attrs["text"])

    def test_query_by_text_case_sense_not_found(self):
        elements = self.pom.get_elements({"text": {"value": "your business", "contains": True}})

        self.assertTrue(len(elements) == 0)

    def test_query_by_text_case_sense_found(self):
        elements = self.pom.get_elements(
            {
                "text": {
                    "value": "your business",
                    "contains": True,
                    "case_sensitive": False,
                }
            }
        )

        self.assertTrue(len(elements) > 0)

        for el in elements:
            self.assertTrue("Your business" in el.attrs["text"])

    def test_query_by_label_and_text(self):
        elements = self.pom.get_elements({"label": "text-btn", "text": "Update"})

        self.assertTrue(len(elements) > 0)

        for el in elements:
            self.assertEqual(el.label, "text-btn")
            self.assertEqual(el.attrs["text"], "Update")

    def test_query_by_label_and_text_not_contains(self):
        elements = self.pom.get_elements({"label": "text-btn", "text": "Updat"})

        self.assertTrue(len(elements) == 0)

    def test_query_invalid(self):
        with self.assertRaisesRegex(Exception, "Query object doesn't have 'value' field"):
            self.pom.get_elements({"label": {"case_sensitive": True}})


class TestCVPOMServer(unittest.TestCase):
    def test_query_server(self):
        app.cv_pom = POM("yolov8n.pt")
        client = TestClient(app)

        image = cv.imread("test/resources/yolo_test_1.png")
        _, base64_image = cv.imencode(".png", image)
        data = base64.b64encode(base64_image).decode()

        response = client.post(
            "/convert_to_cvpom",
            json={"image_base64": data, "ocr": True, "query": {"label": "ocr_element"}},
        )

        response_data = response.json()
        self.assertTrue(len(response_data) > 0, f"the response data was: {response_data}")
        for el in response_data:
            self.assertEqual(el["label"], "ocr_element")


if __name__ == "__main__":
    unittest.main()
