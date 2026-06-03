import numpy as np
import re
import time
import math

class Until:
    def __init__(self, until, action_repeat=1):
        self._until = until
        self._action_repeat = action_repeat

    def __call__(self, step):
        if self._until is None:
            return True
        until = self._until // self._action_repeat
        return step < until

class Every:
    def __init__(self, every, action_repeat=1):
        self._every = every
        self._action_repeat = action_repeat

    def __call__(self, step):
        if self._every is None:
            return False
        every = self._every // self._action_repeat
        if step % every == 0:
            return True
        return False
    
class eval_mode:
    def __init__(self, *models):
        self.models = models

    def __enter__(self):
        self.prev_states = []
        for model in self.models:
            self.prev_states.append(model.training)
            model.train(False)

    def __exit__(self, *args):
        for model, state in zip(self.models, self.prev_states):
            model.train(state)
        return False
    
class mw_discount_step:
    def __init__(self, num_repeats = 2, base_discount = 0.997, decay1 = 0.02, decay2 = 0.007, \
        temp_1 = 500000,temp_2 = 1600000, nstep = 3, nstep_alpha = 7, nstep_temp = 1000000):
        self._num_repeats = num_repeats
        self._base_discount = base_discount
        self._temp_1 = temp_1
        self._temp_2 = temp_2
        self._decay_1 = decay1
        self._decay_2 = decay2
        self._nstep = nstep
        self._nstep_alpha = nstep_alpha
        self._nstep_temp = nstep_temp
        
    def discount(self, global_step):
        global_frame = global_step * self._num_repeats
        decay1 = self._decay_1 * math.exp(-global_frame / self._temp_1)
        decay2 = self._decay_2 * math.exp(-global_frame / self._temp_2)
        return self._base_discount - decay1 - decay2
    
    def nstep(self, global_step):
        global_frame = global_step * self._num_repeats
        return math.floor(self._nstep + self._nstep_alpha * math.exp(-global_frame / self._nstep_temp))

def gaussian_logprob(eps, log_std):
    """Compute Gaussian log probability."""
    residual = -0.5 * eps.pow(2) - log_std
    log_prob = residual - 0.9189385175704956
    return log_prob.sum(-1, keepdim=True)

def tie_weights(src, trg):
    assert type(src) == type(trg)
    trg.weight = src.weight
    trg.bias = src.bias
    
    
def schedule(schdl, step):
    try:
        return float(schdl)
    except ValueError:
        match = re.match(r'linear\((.+),(.+),(.+)\)', schdl)
        if match:
            init, final, duration = [float(g) for g in match.groups()]
            mix = np.clip(step / duration, 0.0, 1.0)
            return (1.0 - mix) * init + mix * final
        match = re.match(r'step_linear\((.+),(.+),(.+),(.+),(.+)\)', schdl)
        if match:
            init, final1, duration1, final2, duration2 = [float(g) for g in match.groups()]
            if step <= duration1:
                mix = np.clip(step / duration1, 0.0, 1.0)
                return (1.0 - mix) * init + mix * final1
            else:
                mix = np.clip((step - duration1) / duration2, 0.0, 1.0)
                return (1.0 - mix) * final1 + mix * final2
    raise NotImplementedError(schdl)

class Timer:
    def __init__(self):
        self._start_time = time.time()
        self._last_time = time.time()

    def reset(self):
        elapsed_time = time.time() - self._last_time
        self._last_time = time.time()
        total_time = time.time() - self._start_time
        return elapsed_time, total_time

    def total_time(self):
        return time.time() - self._start_time