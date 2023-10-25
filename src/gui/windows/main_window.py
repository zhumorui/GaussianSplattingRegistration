import os

from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QSplitter, QWidget, QGroupBox, QVBoxLayout, \
    QTabWidget, QSizePolicy, QErrorMessage

from src.gui.widgets.cache_tab_widget import CacheTab
from src.gui.widgets.global_registration_widget import GlobalRegistrationGroup
from src.gui.widgets.input_tab_widget import InputTab
from src.gui.widgets.local_registration_widget import LocalRegistrationGroup
from src.gui.widgets.merger_widget import MergerWidget
from src.gui.widgets.transformation_widget import Transformation3DPicker
from src.gui.widgets.visualizer_widget import VisualizerWidget
from src.gui.windows.open3d_window import Open3DWindow
from src.gui.workers.qt_workers import PointCloudSaver
from src.utils.file_loader import load_plyfile_pc, check_point_cloud_type, PointCloudType
from src.utils.point_cloud_merger import merge_point_clouds


class RegistrationMainWindow(QMainWindow):

    def __init__(self, parent=None):
        super(RegistrationMainWindow, self).__init__(parent)
        self.setWindowTitle("Gaussian Splatting Registration")

        self.cache_tab = None
        self.input_tab = None
        self.merger_widget = None
        self.visualizer_widget = None
        self.transformation_picker = None
        self.pc_originalFirst = None
        self.pc_originalSecond = None

        working_dir = os.getcwd()
        self.cache_dir = os.path.join(working_dir, "cache")
        self.input_dir = os.path.join(working_dir, "inputs")
        self.output_dir = os.path.join(working_dir, "output")

        # Set window size to screen size
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(screen)

        # Create splitter and two planes
        splitter = QSplitter(self)
        self.pane_open3d = Open3DWindow()
        pane_data = QWidget()

        layout_pane = QVBoxLayout()
        pane_data.setLayout(layout_pane)

        group_input_data = QGroupBox()
        self.setup_input_group(group_input_data)

        group_registration = QGroupBox()
        self.setup_registration_group(group_registration)

        layout_pane.addWidget(group_input_data)
        layout_pane.addWidget(group_registration)

        splitter.addWidget(self.pane_open3d)
        splitter.addWidget(pane_data)

        splitter.setOrientation(1)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 0)

        self.setCentralWidget(splitter)

    def setup_input_group(self, group_input_data):
        group_input_data.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_input_data.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_input_data.setTitle("Inputs and settings")
        layout = QVBoxLayout()
        group_input_data.setLayout(layout)

        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        self.input_tab = InputTab(self.input_dir)
        self.cache_tab = CacheTab(self.cache_dir)
        self.transformation_picker = Transformation3DPicker()
        self.visualizer_widget = VisualizerWidget()
        self.merger_widget = MergerWidget(self.output_dir, self.input_dir)

        self.transformation_picker.transformation_matrix_changed.connect(self.update_point_clouds)
        self.input_tab.result_signal.connect(self.handle_result)
        self.cache_tab.result_signal.connect(self.handle_result)
        self.visualizer_widget.signal_change_vis.connect(self.change_visualizer)
        self.visualizer_widget.signal_get_current_view.connect(self.get_current_view)
        self.merger_widget.signal_merge_point_clouds.connect(self.merge_point_clouds)

        tab_widget.addTab(self.input_tab, "I/O files")
        tab_widget.addTab(self.cache_tab, "Cache")
        tab_widget.addTab(self.transformation_picker, "Transformation")
        tab_widget.addTab(self.visualizer_widget, "Visualizer")
        tab_widget.addTab(self.merger_widget, "Merging")

    def setup_registration_group(self, group_registration):
        group_registration.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_registration.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        group_registration.setLayout(layout)

        layout.addWidget(GlobalRegistrationGroup())
        layout.addWidget(LocalRegistrationGroup())

    # Event Handlers
    def update_point_clouds(self, transformation_matrix):
        if self.visualizer_widget.get_use_debug_color():
            dc1, dc2 = self.visualizer_widget.get_debug_colors()
            self.pane_open3d.update_transform_with_colors(dc1, dc2, transformation_matrix)
        else:
            self.pane_open3d.update_transform(transformation_matrix)

        zoom, front, lookat, up = self.visualizer_widget.get_current_transformations()
        self.pane_open3d.update_visualizer(zoom, front, lookat, up)

    def handle_result(self, pc_first, pc_second, save_point_clouds, original1=None, original2=None):
        error_message = ('Importing one or both of the point clouds failed.\nPlease check that you entered the correct '
                         'path!')
        if self.check_if_none_and_throw_error(pc_first, pc_second, error_message):
            return

        self.pc_originalFirst = original1
        self.pc_originalSecond = original2

        if save_point_clouds:
            worker = PointCloudSaver(pc_first, pc_second)
            worker.run()

        self.pane_open3d.load_point_clouds(pc_first, pc_second)

    def change_visualizer(self, use_debug_color, dc1, dc2, zoom, front, lookat, up):
        if use_debug_color:
            self.pane_open3d.update_transform_with_colors(dc1, dc2, self.transformation_picker.transformation_matrix)

        self.pane_open3d.update_visualizer(zoom, front, lookat, up)

    def get_current_view(self):
        zoom, front, lookat, up = self.pane_open3d.get_current_view()
        self.visualizer_widget.assign_new_values(zoom, front, lookat, up)

    def merge_point_clouds(self, is_checked, pc_path1, pc_path2, merge_path):
        if is_checked:
            pc_first = load_plyfile_pc(pc_path1)
            pc_second = load_plyfile_pc(pc_path2)
            error_message = ("Importing one or both of the point clouds failed.\nPlease check that you entered the "
                             "correct path!")
            if self.check_if_none_and_throw_error(pc_first, pc_second, error_message):
                return

            merge_point_clouds(pc_first, pc_second, merge_path, self.transformation_picker.transformation_matrix)
            return

        # TODO: Check if original point clouds are loaded
        error_message = ("There were no preloaded point clouds found! Load a point cloud before merging, or check the "
                         "\"corresponding inputs\" option and select the point clouds you wish to merge.")
        if self.check_if_none_and_throw_error(self.pc_originalFirst, self.pc_originalSecond, error_message):
            return

        error_message = ("One or both of the point clouds preloaded are not of the correct format. Make sure to load "
                         "non-cached, gaussian output point clouds or use the \"corresponding inputs\" option and "
                         "select the point clouds you wish to merge.")
        if check_point_cloud_type(self.pc_originalFirst) != PointCloudType.gaussian or check_point_cloud_type(
                self.pc_originalSecond) != PointCloudType.gaussian:
            self.check_if_none_and_throw_error(None, None, error_message)
            return

        merge_point_clouds(self.pc_originalFirst, self.pc_originalSecond,
                           merge_path, self.transformation_picker.transformation_matrix)

    def check_if_none_and_throw_error(self, pc_first, pc_second, message):
        if not pc_first or not pc_second:
            # TODO: Further error messages. Tracing?
            dialog = QErrorMessage(self)
            dialog.setWindowTitle("Error")
            dialog.showMessage(message)
            return True

        return False
