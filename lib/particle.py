
class ParticleSystem:
    def __init__(self, particles=[]):
      self.particles = particles

class Particle:

  def __init__(self, x=0.0, y=0.0, xv=0.0, yv=0.0):
    self.x = x
    self.y = y
    self.xv = xv
    self.yv = yv
