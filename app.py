from flask import Flask, render_template, request, send_file, url_for
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer,
    CircleModuleDrawer,
    GappedSquareModuleDrawer
)
from PIL import Image, ImageDraw, ImageFont, ImageColor
import os
import random
import string
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_gradient(width, height, start_color, end_color, direction='horizontal'):
    """Generate a gradient background"""
    base = Image.new('RGBA', (width, height), start_color)
    top = Image.new('RGBA', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []

    if direction == 'horizontal':
        for x in range(width):
            mask_data.extend([int(255 * (x / width))] * height)
    else:
        for y in range(height):
            mask_data.extend([int(255 * (y / height))] * width)

    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base


@app.route('/', methods=['GET', 'POST'])
def index():
    qr_code_url = None
    qr_data = None

    if request.method == 'POST':
        # Get form data
        qr_type = request.form.get('qr_type', 'url')
        content = request.form.get('url', '')
        file = request.files.get('file')
        logo = request.files.get('logo')

        # Color settings
        fill_color = request.form.get('fill_color', '#000000')
        bg_type = request.form.get('bg_type', 'solid')
        bg_color = request.form.get('bg_color', '#ffffff')
        gradient_start = request.form.get('gradient_start', '#ffffff')
        gradient_end = request.form.get('gradient_end', '#000000')
        gradient_direction = request.form.get('gradient_direction', 'horizontal')

        # Design settings
        shape = request.form.get('shape', 'square')
        add_text = 'text' in request.form
        text_content = request.form.get('text_content', '')

        # Handle file uploads
        if qr_type in ['pdf', 'image'] and file and allowed_file(file.filename):
            filename = f"{qr_type}_{generate_random_string()}.{file.filename.split('.')[-1]}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            content = url_for('uploaded_file', filename=filename, _external=True)

        # Generate QR code
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(content)
        qr.make(fit=True)

        # Select module drawer
        if shape == 'circle':
            module_drawer = CircleModuleDrawer()
        elif shape == 'gapped':
            module_drawer = GappedSquareModuleDrawer()
        else:
            module_drawer = SquareModuleDrawer()

        # Create base QR code
        qr_img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            fill_color=fill_color,
            back_color='white'
        ).convert('RGBA')

        # Create background
        width, height = qr_img.size
        if bg_type == 'gradient':
            bg_img = generate_gradient(width, height,
                                       ImageColor.getrgb(gradient_start),
                                       ImageColor.getrgb(gradient_end),
                                       gradient_direction)
        elif bg_type == 'transparent':
            bg_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        else:
            bg_img = Image.new('RGBA', (width, height), ImageColor.getrgb(bg_color))

        # Combine QR code with background
        bg_img.paste(qr_img, (0, 0), qr_img)

        # Add logo centered (always enabled if uploaded)
        if logo and allowed_file(logo.filename):
            try:
                logo_img = Image.open(logo).convert('RGBA')
                # Resize logo to 25% of QR code size
                logo_size = min(width // 4, height // 4)
                logo_img.thumbnail((logo_size, logo_size), Image.LANCZOS)

                # Calculate centered position
                logo_pos = (
                    (width - logo_img.width) // 2,
                    (height - logo_img.height) // 2
                )

                # Paste logo with transparency
                bg_img.paste(logo_img, logo_pos, logo_img)
            except Exception as e:
                print(f"Error adding logo: {e}")

        # Add text with proper textsize method
        if add_text and text_content:
            try:
                draw = ImageDraw.Draw(bg_img)
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()

                # Use textbbox instead of textsize
                bbox = draw.textbbox((0, 0), text_content, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                text_pos = (
                    (width - text_width) // 2,
                    height - text_height - 20
                )
                draw.text(text_pos, text_content, fill=fill_color, font=font)
            except Exception as e:
                print(f"Error adding text: {e}")

        # Save and return
        filename = f"qr_{generate_random_string()}.png"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        bg_img.save(save_path)

        qr_code_url = url_for('uploaded_file', filename=filename)
        qr_data = content

    return render_template('index.html',
                           qr_code_url=qr_code_url,
                           qr_data=qr_data)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


if __name__ == '__main__':
    app.run(debug=True)