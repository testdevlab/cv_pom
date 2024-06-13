import argparse
import os
import uvicorn
import base64
import cv2
import numpy as np

from cv_pom.cv_pom import POM
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
# Put "cv_pom" inside of app object in order to make in testable (see cv_pom_text.py TestCVPOMServer test case)
app.cv_pom = None


class ConvertBody(BaseModel):
    image_base64: str
    ocr: dict
    query: dict


def parse_args():
    parser = argparse.ArgumentParser(description="CV POM wrapper")
    parser.add_argument("--model", help="The CV model to be used [path]")
    args = parser.parse_args()

    if not args.model:
        print("Please specify the model")
        exit(1)

    args.model = os.path.expanduser(args.model)
    if not os.path.exists(args.model):
        print("The model path does not exist")
        exit(1)

    return args


@app.post("/convert_to_cvpom")
async def upload(args: ConvertBody):
    try:
        im_bytes = base64.b64decode(args.image_base64)
        im_arr = np.frombuffer(im_bytes, dtype=np.uint8)  # im_arr is one-dim Numpy array
        img = cv2.imdecode(im_arr, flags=cv2.IMREAD_COLOR)
    except Exception as err:
        raise HTTPException("400", f"Failed to uploading file: {err}")

    try:
        app.cv_pom.convert_to_cvpom(img, args.ocr)
    except Exception as err:
        raise HTTPException("400", f"Failed to create POM: {err}")

    try:
        elements = app.cv_pom.get_elements(args.query)
    except Exception as err:
        raise HTTPException("400", f"Failed to query elements: {err}")

    return [el.as_dict() for el in elements]


if __name__ == "__main__":
    model = parse_args().model
    app.cv_pom = POM(model)
    uvicorn.run(app, host="127.0.0.1", port=8000)
