import numpy as np

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    CircleStimulus,
    PositionStimulus,
    InterpolatedStimulus,
)


class ClosedLoop1D(BackgroundStimulus, InterpolatedStimulus, DynamicStimulus):
    """
    Vigor-based closed loop stimulus. Velocity is assumend to be calculated
    with the

    The parameters can change in time if the df_param is supplied which
    specifies their values in time.

    Parameters
    ----------
    base_vel:
        the velocity of the background when the stimulus is not moving
    gain:
        the closed-loop gain, a gain of 1 approximates
        the freely-swimming behaviour
    lag:
        how much extra delay is provided in the closed loop
    shunting: bool
        if true, when the fish stops swimming its infulence on the
        background motion stops, immediately independent of lag
    swimming_threshold: float
        the velocity at which the fish is considered to be performing
        a bout
    fixed_vel: float
        if not None, fixed velocity for the stimulus when fish swims
    """

    def __init__(
        self,
        *args,
        base_vel=10,
        gain=1,
        lag=0,
        shunting=False,
        swimming_threshold=0.2 * -30,
        fixed_vel=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.name = "closed loop 1D"
        self.fish_velocity = 0
        self.dynamic_parameters = ["vel", "fish_velocity", "gain"]
        self.base_vel = base_vel
        self.fish_velocity = 0
        self.vel = base_vel
        self.lag = lag
        self.gain = gain
        self.swimming_threshold = swimming_threshold
        self.fish_swimming = False
        self.shunting = shunting
        self.shunted = False
        self.fixed_velocity = fixed_vel

        self.bout_start = None
        self.bout_stop = None

        self._past_t = 0

    def update(self):
        """
        Here we use fish velocity to change velocity of gratings.
        """
        super().update()

        self.fish_velocity = self._experiment.estimator.get_velocity(lag=self.lag)

        if self.base_vel == 0:
            self.shunted = False
            self.fish_swimming = False

        if (
            self.shunting
            and self.fish_swimming
            and self.fish_velocity > self.swimming_threshold
        ):
            self.shunted = True

        # If estimated velocity greater than threshold
        # the fish is performing a bout
        if self.fish_velocity < self.swimming_threshold:
            self.fish_swimming = True

            if self.bout_start is None:
                self.bout_start = self._elapsed
            self.bout_stop = None
        else:
            self.bout_start = None
            if self.bout_start is None:
                self.bout_start = self._elapsed

            self.fish_swimming = False

        if self.fixed_velocity is None:
            self.vel = int(not self.shunted) * (
                self.base_vel - self.fish_velocity * self.gain * int(self.fish_swimming)
            )
        else:
            if self.fish_swimming and not self.base_vel == 0:
                self.vel = self.fixed_velocity
            else:
                self.vel = self.base_vel

        if self.vel is None or self.vel > 50:
            self.vel = 0

        self.x += self._dt * self.vel


class PerpendicularMotion(BackgroundStimulus, InterpolatedStimulus, DynamicStimulus):
    """ A stimulus which is always kept perpendicular to the fish

    """

    def update(self):
        x, y, theta = self._experiment.estimator.get_position()
        if np.isfinite(theta):
            self.theta = theta
        super().update()


class FishTrackingStimulus(PositionStimulus):
    def update(self):
        y, x, theta = self._experiment.estimator.get_position()
        if np.isfinite(theta):
            self.x = x
            self.y = y
            self.theta = theta
        super().update()


class CenteringWrapper(PositionStimulus):
    """ A meta-stimulus which turns on centering if the fish
    veers too much towrds the edge

    """

    def __init__(self, stimulus, centering, margin=200, **kwargs):
        super().__init__(**kwargs)
        self.margin = margin**2
        self.stimulus = stimulus
        self.active = self.stimulus
        self.centering = centering
        self.xc = 320
        self.yc = 240
        self.duration = self.stimulus.duration

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self.stimulus.initialise_external(experiment)
        self.centering.initialise_external(experiment)

    def update(self):
        y, x, theta = self._experiment.estimator.get_position()
        if x < 0 or ((x - self.xc) ** 2 + (y - self.yc) ** 2 ) > self.margin:
            self.active = self.centering
        else:
            self.active = self.stimulus
        self.active._elapsed = self._elapsed
        self.active.update()

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        self.active.paint(p, w, h)


class TrackingStimulus(CircleStimulus):
    def update(self):
        self.x, self.y, _ = self._experiment.estimator.get_position()
        super().update()
