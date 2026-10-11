from isaaclab.envs.direct_rl_env import DirectRLEnv

from env.environment.isaac.compat import render_sim


class CustomDirectRLEnv(DirectRLEnv):
    def _needs_render(self) -> bool:
        # Isaac Lab 3.0 exposes a cached ``is_rendering`` property; 2.3 needs the explicit query.
        if hasattr(self.sim, "is_rendering"):
            return bool(self.sim.is_rendering)
        return self.sim.has_gui() or self.sim.has_rtx_sensors()

    def sim_step(self, render: bool = True):
        is_rendering = self._needs_render()

        for _ in range(self.cfg.decimation):
            self._sim_step_counter += 1
            self.scene.write_data_to_sim()
            self.sim.step(render=False)
            if (
                self.cfg.sim.render_interval > 0
                and self._sim_step_counter % self.cfg.sim.render_interval == 0
                and is_rendering
                and render
            ):
                render_sim(self.sim)
            self.scene.update(dt=self.physics_dt)

        self.episode_length_buf += 1
        self.common_step_counter += 1

        if self.cfg.events:
            if "interval" in self.event_manager.available_modes:
                self.event_manager.apply(mode="interval", dt=self.step_dt)

        return self.extras
