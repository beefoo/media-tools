from lib.clip import *
from lib.math_utils import *

class Sampler:

    availableSamples = [
        # hip hop kick
        {"name": "kick", "style": "hiphop1", "files": ["jay_z_all_i_need_kick_01.wav", "jay_z_all_i_need_kick_02.wav"]},
        {"name": "kick", "style": "hiphop2", "files": ["jay_z_blueprint_kick_01.wav", "jay_z_blueprint_kick_02.wav"]},
        {"name": "kick", "style": "hiphop3", "files": ["jay_z_rulers_back_kick_01.wav", "jay_z_rulers_back_kick_02.wav"]},
        # hip hop snare
        {"name": "snare", "style": "hiphop1", "files": ["jay_z_all_i_need_snare_01.wav"]},
        {"name": "snare", "style": "hiphop2", "files": ["jay_z_blueprint_snare_01.wav", "jay_z_blueprint_snare_02.wav"]},
        {"name": "snare", "style": "hiphop3", "files": ["jay_z_rulers_back_snare_01.wav", "jay_z_rulers_back_snare_02.wav"]},
        {"name": "snare", "style": "hiphop4", "files": ["jay_z_izzo_snare_01.wav", "jay_z_izzo_snare_02.wav", "jay_z_izzo_snare_03.wav"]},
        # hip hop hat
        {"name": "hat", "style": "hiphop1", "files": ["jay_z_all_i_need_hat_01.wav", "jay_z_all_i_need_hat_02.wav"]},
        {"name": "hat", "style": "hiphop2", "files": ["jay_z_blueprint_hat_01.wav", "jay_z_blueprint_hat_02.wav"]},
        # rock kick
        {"name": "kick", "style": "rock1", "files": ["lcd_time_to_get_away_kick_01.wav", "lcd_time_to_get_away_kick_02.wav", "lcd_time_to_get_away_kick_03.wav", "lcd_time_to_get_away_kick_04.wav"]},
        {"name": "kick", "style": "rock2", "files": ["lcd_sound_of_silver_kick_01.wav"]},
        {"name": "kick", "style": "rock3", "files": ["lcd_us_vs_them_kick_01.wav", "lcd_us_vs_them_kick_02.wav", "lcd_us_vs_them_kick_03.wav", "lcd_us_vs_them_kick_04.wav"]},
        # rock snare
        {"name": "snare", "style": "rock1", "files": ["lcd_time_to_get_away_snare_01.wav", "lcd_time_to_get_away_snare_02.wav"]},
        {"name": "snare", "style": "rock2", "files": ["lcd_sound_of_silver_snare_01.wav"]},
        {"name": "snare", "style": "rock3", "files": ["daft_punk_doing_it_right_snare_01.wav", "daft_punk_doing_it_right_snare_02.wav"]},
        # rock hat
        {"name": "hat", "style": "rock1", "files": ["lcd_time_to_get_away_hat_01.wav", "lcd_time_to_get_away_hat_02.wav"]},
        {"name": "hat", "style": "rock2", "files": ["lcd_sound_of_silver_hat_01.wav"]},
        # rock tom
        {"name": "tom", "style": "rock1", "files": ["lcd_sound_of_silver_tom_01.wav", "lcd_sound_of_silver_tom_02.wav"]},
        # rock stick
        {"name": "stick", "style": "rock1", "files": ["lcd_watch_the_tapes_stick_01.wav"]},
    ]

    def __init__(self, props={}):
        defaults = {
            "sampleDir": "media/sampler/",
            "kick": "rock2",
            "snare": "hiphop2",
            "hat": "hiphop2",
            "tom": "rock1",
            "stick": "rock1",
            "clipParams": {
                "fadeOut": 10,
                "fadeIn": 10,
                "reverb": 80
            }
        }
        defaults.update(props)
        self.props = defaults
        self.clips = {}
        self.defaultClipParams = defaults["clipParams"]

    def getClips(self):
        allClips = []
        for name, style in self.clips:
            allClips += self.clips[name, style]
        return allClips

    def getSamples(self, name, style="default"):
        if style=="default":
            style = self.props[name]

        samples = [s for s in self.availableSamples if s["name"]==name and s["style"]==style]
        if len(samples) <= 0:
            print("cannot find %s with style %s" % (name, style))
            return False

        files = samples[0]["files"]
        fileCount = len(files)
        fileDir = self.props["sampleDir"]

        samples = [{
            "filename": fileDir + f
        } for f in files]

        return samples

    def loadClips(self, name, style="default"):
        if (name, style) in self.clips:
            return self.clips[(name, style)]

        samples = self.getSamples(name, style)

        self.clips[(name, style)] = [Clip(s) for s in samples]
        return self.clips[(name, style)]

    def queuePlay(self, ms, name, style="default", index=0, params={}):
        clips = self.loadClips(name, style)
        clipCount = len(clips)

        if clipCount > 0:
            dparams = self.defaultClipParams.copy()
            dparams.update(params)
            clips[int(index % clipCount)].queuePlay(ms, dparams)
        else:
            print("No %s clips loaded with style %s" % (name, style))
