from pydub import AudioSegment

sound = AudioSegment.from_file("../media/sample/dolbycanyon.mp4", format="mp4")
print(len(sound))
