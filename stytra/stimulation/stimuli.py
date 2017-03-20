import numpy as np
from PyQt5.QtGui import QImage
import qimage2ndarray
from PyQt5.QtGui import QPainter, QImage
from PyQt5.QtCore import QPoint
import cv2
from time import sleep
from stytra.hardware.serial import PyboardConnection


class Stimulus:
    """ General class for a stimulus."""
    def __init__(self, duration=0.0):
        """ Make a stimulus, with the basic properties common to all stimuli
        Initial values which do not change during the stimulus
        are prefixed with _, so that they are not logged
        at every time step

        :param output_shape:
        :param duration:
        """
        self._started = None
        self.elapsed = 0.0
        self.duration = duration
        self.name = ''

    def get_state(self):
        """ Returns a dictionary with stimulus features """
        state_dict = dict()
        for key, value in self.__dict__.items():
            if not callable(value) and key[0] != '_':
                state_dict[key] = value

        return state_dict

    def update(self):
        pass

    def start(self):
        pass


class ImageStimulus(Stimulus):
    def __init__(self, output_shape=(100, 100), **kwargs):
        super().__init__(**kwargs)
        self.output_shape = output_shape

    def get_image(self):
        pass


class Flash(ImageStimulus):
    """ Flash stimulus """
    def __init__(self, *args, color=(255, 255, 255), **kwargs):
        super(Flash, self).__init__(*args, **kwargs)
        self.color = color
        self.name = 'Whole field'
        self._imdata = np.ones(self.output_shape + (3,), dtype=np.uint8) * \
                       np.array(self.color, dtype=np.uint8)[None, None, :]


    def get_image(self):
        self._imdata = np.ones(self.output_shape + (3,), dtype=np.uint8) * \
                       np.array(self.color, dtype=np.uint8)[None, None, :]

        return self._imdata


class Pause(Flash):
    def __init__(self, *args, **kwargs):
        super(Pause, self).__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = 'Pause'


class PainterStimulus(Stimulus):
    def paint(self, p):
        pass


class SeamlessStimulus(ImageStimulus):
    def __init__(self, *args, background=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = 0
        self.y = 0
        self.theta = 0
        self._background = background

    def _transform_mat(self):
        if self.theta == 0:
            return np.array([[1, 0, self.y],
                             [0, 1, self.x]]).astype(np.float32)
        else:
            return np.array([[np.cos(self.theta), -np.sin(self.theta), self.y],
                             [np.sin(self.theta), np.cos(self.theta), self.x]]).astype(np.float32)

    def get_image(self):
        self.update()
        to_display = cv2.warpAffine(self._background, self._transform_mat(),
                                    borderMode=cv2.BORDER_WRAP,
                                    dsize=self.output_shape)
        return to_display


class MovingSeamless(SeamlessStimulus):
    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = motion

    def update(self):
        self.x = np.interp(self.elapsed, self.motion.t, self.motion.x)
        self.y = np.interp(self.elapsed, self.motion.t, self.motion.y)


class MovingConstantly(SeamlessStimulus):
    def __init__(self, *args, x_vel=0, y_vel=0, mm_px=1, monitor_rate=60, **kwargs):
        """
        :param x_vel: x drift velocity (mm/s)
        :param y_vel: x drift velocity (mm/s)
        :param mm_px: mm per pixel
        :param monitor_rate: monitor rate (in Hz)
        """
        super().__init__(*args, **kwargs)
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.x_shift_frame = (x_vel/mm_px)/monitor_rate
        self.y_shift_frame = (y_vel/mm_px)/monitor_rate


    def update(self):
        self.x += self.x_shift_frame
        self.y += self.y_shift_frame


class DynamicStimulus(Stimulus):
    pass


class ClosedLoopStimulus(DynamicStimulus):
    pass


class ClosedLoop1D(DynamicStimulus):
    def update(self):
        pass


class ShockStimulus(Stimulus):
    def __init__(self, burst_freq=50, pulse_amp=3, burst_n=5, pulse_dur_ms=2, pyboard=None, **kwargs):
        super().__init__(**kwargs)
        assert isinstance(pyboard, PyboardConnection)
        self._pyb = pyboard
        self.burst_freq = burst_freq
        self.pulse_dur_ms = pulse_dur_ms
        self.burst_n = burst_n
        self.pulse_amp_mA = pulse_amp
        self.pause = 1/burst_freq - pulse_dur_ms/1000

        amp_dac = str(int(255*pulse_amp/3.5))
        pulse_dur_str = str(pulse_dur_ms).zfill(3)
        self.mex = str('shock' + amp_dac + pulse_dur_str)


    def start(self):
        for i in range(self.burst_n):
            self._pyb.write("shock218002")
            sleep(self.pause)

        self.elapsed = 1


if __name__ == '__main__':
    pyb = PyboardConnection(com_port='COM3')
    stim = ShockStimulus(pyboard=pyb)
    stim.run()

