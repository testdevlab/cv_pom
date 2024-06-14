import argparse
import os
import sys
import cv2 as cv
from cv_pom.cv_pom import POM


def parse_args():
    parser = argparse.ArgumentParser(description="CV POM wrapper")
    parser.add_argument("--model", help="The CV model to be used [path]")
    parser.add_argument("--media", help="The media file [path]")
    parsed_args = parser.parse_args()

    if not parsed_args.model or not parsed_args.media:
        print("Please specify both the model and media")
        exit(1)

    parsed_args.model = os.path.expanduser(parsed_args.model)
    parsed_args.media = os.path.expanduser(parsed_args.media)
    if not os.path.exists(parsed_args.model):
        print("The model path does not exist")
        exit(1)

    if not os.path.exists(parsed_args.media):
        print("The media path does not exist")
        exit(1)

    return parsed_args


if __name__ == "__main__":
    args = parse_args()
    cv_pom = POM(args.model)
    ocr_props_comb = {'paragraph': False}
    cv_pom.convert_to_cvpom(args.media, ocr_props_comb)

    if len(cv_pom.get_elements()) == 0:
        print(f"No object was found in the image: {args.media}")
        sys.exit()

    print(cv_pom.to_json())

    cv.imshow("Annotated image", cv_pom.annotated_frame)
    cv.waitKey(0)
