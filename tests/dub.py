# from pydub import AudioSegment
#
# sound = AudioSegment.from_file("../media/sample/dolbycanyon.mp4", format="mp4")
# print(len(sound))

from moviepy.editor import VideoFileClip
video = VideoFileClip("E:/landscapes/downloads/ia_politicaladarchive/PolAd_DonaldTrump_c0h66.mp4", audio=False)
videoDur = video.duration
print(videoDur)
