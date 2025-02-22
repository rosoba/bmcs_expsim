import bmcs_utils.api as bu
import traits.api as tr
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


# This was not directly working
class DICInpLDTime(bu.Model):
    """
    Load cell input channel.
    """
    name = 'DIC load-deflection input channel'

    dir_name = bu.Str('<unnamed>', ALG=True)
    """Directory name containing the test data.
    """
    def _dir_name_change(self):
        self.name = f'Test {self.name}'
        self._set_dic_params()

    time_0 = bu.Float( ALG=True)
    """Initial time
    """

    time_1 = tr.Property(depends_on='state_changed')
    """Final time
    """
    @tr.cached_property
    def _get_time_1(self):
        time_m, _, _ = self.time_F_w_m
        return time_m[-1]

    time_m_skip = bu.Int(10, ALG=True)
    """Jump over the specified number of steps
    """

    ipw_view = bu.View(
        bu.Item('time_0', readonly=True),
        bu.Item('time_1', readonly=True),
        bu.Item('time_m_skip'),
        bu.Item('n_m', readonly=True),
    )

    base_dir = tr.Directory
    def _base_dir_default(self):
        return Path.home() / 'simdb' / 'data' / 'shear_zone'

    data_dir = tr.Property
    """Directory with the data"""
    def _get_data_dir(self):
        return Path(self.base_dir) / self.dir_name

    time_F_w_data_dir = tr.Property
    """Directory with the load deflection data"""
    def _get_time_F_w_data_dir(self):
        return self.data_dir / 'load_deflection'

    time_F_w_file_name = tr.Str('load_deflection.csv')
    """Name of the file with the measured load deflection data
    """

    time_F_w_m = tr.Property(depends_on='state_changed')
    """Read the load displacement values from the individual 
    csv files from the test
    """
    @tr.cached_property
    def _get_time_F_w_m(self):
        time_F_w_file = self.time_F_w_data_dir / self.time_F_w_file_name
        time_F_w_m = np.array(pd.read_csv(time_F_w_file, decimal=",", skiprows=1,
                              delimiter=None), dtype=np.float_)
        time_m, F_m, w_m = time_F_w_m[::self.time_m_skip, (0,1,2)].T
        F_m *= -1

        argtime_0 = np.argmax(time_m > self.time_0)
        time_m, F_m, w_m = time_m[argtime_0:], F_m[argtime_0:], w_m[argtime_0:]

        argmax_F_m = np.argmax(F_m)
        asc_time_m, asc_F_m, asc_w_m = self._get_asc_time_F_w(time_m[:argmax_F_m], F_m[:argmax_F_m], w_m[:argmax_F_m])

        # End data criterion - generalize to introduce a logical condition to identify the final index
        argmax_w_m = np.argmax(w_m)
        dsc_time_m, dsc_F_m, dsc_w_m = time_m[argmax_F_m:argmax_w_m+1], F_m[argmax_F_m:argmax_w_m+1], w_m[argmax_F_m:argmax_w_m+1]
        return np.hstack([asc_time_m, dsc_time_m]), np.hstack([asc_F_m, dsc_F_m]), np.hstack([asc_w_m, dsc_w_m])
    

    def _get_asc_time_F_w(self, time_, F_, w_):
        dF_dic = F_[np.newaxis, :] - F_[:, np.newaxis]
        dF_up_dic = np.triu(dF_dic > 0, 0)
        argmin_dic = np.argmin(dF_up_dic, axis=0)
        for n in range(len(argmin_dic)):
            dF_up_dic[argmin_dic[n]:, n] = False
        asc_dic = np.unique(np.argmax(np.triu(dF_up_dic, 0) > 0, axis=1))
        return time_[asc_dic], F_[asc_dic], w_[asc_dic]
    
    
    time_F_m = tr.Property(depends_on='state_changed')
    """time and force
    """
    @tr.cached_property
    def _get_time_F_m(self):
        time_m, F_m, _ = self.time_F_w_m
        return time_m, F_m

    w_m = tr.Property(depends_on='state_changed')
    """time and force
    """
    @tr.cached_property
    def _get_w_m(self):
        _, _, w_m = self.time_F_w_m
        return w_m

    n_m = tr.Property(bu.Int, depends_on='state_changed')
    """Number of machine time sampling points up to the peak load 
    """
    def _get_n_m(self):
        time_m, _ = self.time_F_m
        return len(time_m)

    f_F_time = tr.Property(depends_on="state_changed")
    @tr.cached_property
    def _get_f_F_time(self):
        """Return the load for a specified time"""
        time_m, F_m, _ = self.time_F_w_m
        return interp1d(time_m, F_m, kind='linear', bounds_error=False, fill_value=(0, 0))


    argmax_F_m = tr.Property(depends_on="state_changed")
    @tr.cached_property
    def _get_argmax_F_m(self):
        _, F_m, _ = self.time_F_w_m
        return np.argmax(F_m)

    argmax_F_time = tr.Property(depends_on="state_changed")
    @tr.cached_property
    def _get_argmax_F_time(self):
        """Return the time for the maximum load"""
        time_m, F_m, _ = self.time_F_w_m
        argmax_F_m = self.argmax_F_m
        return time_m[argmax_F_m]
    
    argmax_w_time = tr.Property(depends_on='state_changed')
    @tr.cached_property
    def _get_argmax_w_time(self):
        """Return the time for the maximum load"""
        time_m, _, w_m = self.time_F_w_m
        return time_m

    f_time_F = tr.Property(depends_on="state_changed")
    """Return the times array for ascending load from zero to maximum"""
    @tr.cached_property
    def _get_f_time_F(self):
        time_m, F_m, _ = self.time_F_w_m
        argmax_F_m = self.argmax_F_m
        return interp1d(F_m[:argmax_F_m+1], time_m[:argmax_F_m+1], kind='linear', 
                        bounds_error=True) 

    f_w_time = tr.Property(depends_on="state_changed")
    @tr.cached_property
    def _get_f_w_time(self):
        time_m, _, w_m = self.time_F_w_m
        return interp1d(time_m, w_m, kind='linear', bounds_error=True)

    f_time_w = tr.Property(depends_on="state_changed")
    """Return the times array for ascending deflection from zero to maximum"""
    @tr.cached_property
    def _get_f_time_w(self):
        time_m, _, w_m = self.time_F_w_m
        return interp1d(w_m, time_m, kind='linear', bounds_error=True)

    n_F = bu.Int(30, ALG=True)

    slices_T = tr.Property(depends_on='state_changed')
    @tr.cached_property
    def _get_slices_T(self):
        argmax_F_m = self.argmax_F_m
        step = int((argmax_F_m - 0) / (self.n_T - 1))
        asc_slice = slice(None, argmax_F_m, step)
        dsc_slice = slice(argmax_F_m, -1, step)
        return asc_slice, dsc_slice

    n_T = bu.Int(100, ALG=True)

    F_T = tr.Property(depends_on='state_changed')
    @tr.cached_property
    def _get_F_T(self):
        _, F_m, _ = self.time_F_w_m
        return np.hstack([F_m[slice_] for slice_ in self.slices_T])

    w_T = tr.Property(depends_on='state_changed')
    @tr.cached_property
    def _get_w_T(self):
        _, _, w_m = self.time_F_w_m
        return np.hstack([w_m[slice_] for slice_ in self.slices_T])


    time_T = tr.Property(depends_on='state_changed')
    @tr.cached_property
    def _get_time_T(self):
        time_m, _, _ = self.time_F_w_m
        return np.hstack([time_m[slice_] for slice_ in self.slices_T])

    def plot_load_deflection(self, ax_load):
        w_m = self.w_m
        _, F_m = self.time_F_m
        argmax_F_m = np.argmax(F_m)

        # ax_load.plot(w_m[:argmax_F_m], F_m[:argmax_F_m], color='black')
        ax_load.plot(w_m, F_m, color='black')
        ax_load.set_ylabel(r'$F$ [kN]')
        ax_load.set_xlabel(r'$w$ [mm]')

        # annotate the maximum load level
        max_F = F_m[argmax_F_m]
        argmax_w_F = w_m[argmax_F_m]
        ax_load.annotate(f'$F_{{\max}}=${max_F:.1f} kN,\nw={argmax_w_F:.2f} mm',
                    xy=(argmax_w_F, max_F), xycoords='data',
                    xytext=(0.05, 0.95), textcoords='axes fraction',
                    horizontalalignment='left', verticalalignment='top',
                    )

    def plot_time_F(self, ax):
        time, F, _ = self.time_F_w_m
        ax.plot(time, F, color='red', label='F')
        ax.set_ylabel(r'$F$/mm')
        ax.set_xlabel(r'time/ms')
        ax.scatter([self.argmax_F_time],[F[self.argmax_F_m]])
        ax.legend()

    def plot_time_w(self, ax):
        time, _, w = self.time_F_w_m
        ax.plot(time, w, color='blue', label='w')
        ax.set_ylabel(r'$w$/mm')
        ax.legend()

    def subplots(self, fig):
        ax_time_F, ax_Fw = fig.subplots(1, 2)
        ax_time_w = ax_time_F.twinx()
        return ax_Fw, ax_time_F, ax_time_w

    def update_plot(self, axes):
        ax_Fw, ax_time_F, ax_time_w = axes
        self.plot_load_deflection(ax_Fw)
        self.plot_time_F(ax_time_F)
        self.plot_time_w(ax_time_w)
