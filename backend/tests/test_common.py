from io import BytesIO

from PIL import Image

from backend.common.utils import coerce_text, compress_image, create_meal_prompt


def _png_bytes(size, mode="RGBA"):
    buffer = BytesIO()
    Image.new(mode, size, color=(200, 100, 50, 255) if mode == "RGBA" else 128).save(
        buffer, format="PNG"
    )
    return buffer.getvalue()


def test_coerce_text_handles_model_output_shapes():
    assert coerce_text(None) == ""
    assert coerce_text("Drink water.") == "Drink water."
    assert coerce_text(["Walk more.", None, "", "Sleep early."]) == "Walk more. Sleep early."
    assert coerce_text({"tip": "Eat fiber"}) == '{"tip": "Eat fiber"}'
    assert coerce_text(42) == "42"


def test_compress_image_downscales_and_reencodes_as_jpeg():
    original = _png_bytes((1600, 1200))

    compressed = compress_image(original)

    with Image.open(BytesIO(compressed)) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"
        assert max(img.size) == 800
        assert img.size == (800, 600)


def test_compress_image_keeps_small_images_at_original_size():
    compressed = compress_image(_png_bytes((300, 200), mode="L"))

    with Image.open(BytesIO(compressed)) as img:
        assert img.format == "JPEG"
        assert img.size == (300, 200)


def test_compress_image_returns_input_when_bytes_are_not_an_image():
    data = b"not an image"
    assert compress_image(data) is data


def test_create_meal_prompt_includes_profile_meal_type_and_allergies():
    prompt = create_meal_prompt(
        {"gender": "female", "weight": 60, "height": 165, "goal": "maintain"},
        meal_type="lunch",
        user_allergies=["peanuts", "gluten"],
    )

    assert "60 kg" in prompt
    assert "Meal type: Lunch" in prompt
    assert "Known allergies: peanuts, gluten" in prompt
    assert '"allergiesDetected"' in prompt
