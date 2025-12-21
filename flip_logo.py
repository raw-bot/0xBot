import sys

from PIL import Image


def flip_image(input_path, output_path):
    try:
        img = Image.open(input_path)
        # Flip the image horizontally (left to right)
        flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)
        flipped_img.save(output_path)
        print(f"Successfully flipped image to {output_path}")
    except Exception as e:
        print(f"Error flipping image: {e}")


if __name__ == "__main__":
    flip_image(
        "/Users/cube/Documents/00-code/0xBot/assets/logos/temp_to_flip.png",
        "/Users/cube/Documents/00-code/0xBot/assets/logos/logo_flipped_script.png",
    )
