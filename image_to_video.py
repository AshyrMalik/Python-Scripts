import os
import argparse
from moviepy.editor import *


def create_video_from_images(
        image_folder,
        output_file="output.mp4",
        fps=30,
        duration=5,
        template="slide_in",
        background_color=(0, 0, 0),
        resolution=(1920, 1080),
        audio_file=None
):
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif'))]
    image_files.sort()

    if not image_files:
        print(f"No image files found in {image_folder}")
        return

    total_duration = len(image_files) * duration
    background = ColorClip(resolution, color=background_color, duration=total_duration)
    clips = []

    for i, img_file in enumerate(image_files):
        img_path = os.path.join(image_folder, img_file)
        try:
            img_clip = ImageClip(img_path)
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            continue

        # Calculate maximum possible size while maintaining aspect ratio
        img_w, img_h = img_clip.size
        ratio = min(resolution[0] / img_w, resolution[1] / img_h)
        max_size = (int(img_w * ratio), int(img_h * ratio))

        # Create zoom animation
        if template == "zoom":
            # Start at 80% size and zoom to 120% over clip duration
            zoom_factor = lambda t: 0.8 + (0.4 * (t / duration))
            img_clip = img_clip.resize(lambda t: zoom_factor(t)).set_position('center')

            # Set actual displayed size to handle overflow
            display_size = (int(max_size[0] * 1.2), int(max_size[1] * 1.2))
            img_clip = img_clip.resize(display_size)
        else:
            img_clip = img_clip.resize(max_size)

        img_clip = img_clip.set_duration(duration).set_start(i * duration)
        clips.append(img_clip)

    video = CompositeVideoClip([background] + clips, size=resolution)

    if audio_file and os.path.exists(audio_file):
        try:
            audio = AudioFileClip(audio_file)
            if audio.duration < video.duration:
                audio = audio.fx(vfx.loop, duration=video.duration)
            else:
                audio = audio.subclip(0, video.duration)
            video = video.set_audio(audio)
        except Exception as e:
            print(f"Error adding audio: {e}")

    try:
        print(f"Creating video with {len(clips)} images")
        video.write_videofile(
            output_file,
            fps=fps,
            codec='libx264',
            audio_codec='aac' if audio_file else None
        )
        print(f"Video saved as {output_file}")
    except Exception as e:
        print(f"Error creating video: {e}")


# Keep the main() function from previous version unchanged
def main():
    parser = argparse.ArgumentParser(description='Create video from images with specified template')
    parser.add_argument('image_folder', help='Folder containing images')
    parser.add_argument('--output', '-o', default='output.mp4', help='Output video file')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second')
    parser.add_argument('--duration', '-d', type=float, default=3, help='Duration per image in seconds')
    parser.add_argument('--template', '-t', choices=['slide_in', 'fade', 'zoom', 'rotate', 'custom'],
                        default='slide_in', help='Animation template')
    parser.add_argument('--width', type=int, default=1920, help='Video width')
    parser.add_argument('--height', type=int, default=1080, help='Video height')
    parser.add_argument('--bg-color', nargs=3, type=int, default=[0, 0, 0],
                        help='Background color as R G B (0-255)')
    parser.add_argument('--audio', help='Audio file to add to the video')

    args = parser.parse_args()

    create_video_from_images(
        args.image_folder,
        output_file=args.output,
        fps=args.fps,
        duration=args.duration,
        template=args.template,
        background_color=tuple(args.bg_color),
        resolution=(args.width, args.height),
        audio_file=args.audio
    )


if __name__ == "__main__":
    main()