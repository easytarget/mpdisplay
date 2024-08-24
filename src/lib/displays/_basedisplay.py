# SPDX-FileCopyrightText: 2024 Brad Barnett and Kevin Schlosser
#
# SPDX-License-Identifier: MIT

# SPDX-FileCopyrightText: 2024 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""
MPDisplay is a module that provides a display interface for various environments
It allows you to interact with different display devices and handle events.

Supported display classes:
- 'BusDisplay': Uses a bus library such as lcd_bus or CircuitPython's DisplayIO buses
- 'DTDisplay': Automatically selects the correct desktop display to use
    - 'SDLDisplay': Uses the SDL2 library
    - 'PGDisplay': Uses the Pygame library
- 'FBDisplay': Uses a framebuffer object such as CircuitPython's framebuffers
- 'JNDisplay': Uses a Jupyter Notebook
- 'PSDisplay': Uses PyScript
"""
from area import Area
import colors  # noqa: F401
import gc
from sys import implementation

np = False
try:
    import ulab.numpy as np  # type: ignore
except ImportError:
    try:
        import numpy as np
    except ImportError:
        pass

viper = False
if implementation.name == "micropython":
    try:
        from _basedisplay_viper import swap_bytes
        viper = True
    except Exception as e:
        print(f"MPDisplay:  {e}")

if not viper:
    if np:
        from _basedisplay_numpy import swap_bytes
    else:
        def swap_bytes(buf, buf_size_pix):
            buf[::2], buf[1::2] = buf[1::2], buf[::2]


gc.collect()

class _BaseDisplay:
    def __init__(self):
        gc.collect()
        self._vssa = False  # False means no vertical scroll
        self._requires_byte_swap = False
        self._auto_byte_swap_enabled = self._requires_byte_swap
        self._touch_device = None
        print(f"{self.__class__.__name__} initialized.")
        gc.collect()

    def __del__(self):
        """
        Deinitializes the display instance.
        """
        self.deinit()

    ############### Universal API Methods, not usually overridden ################

    @property
    def width(self):
        """The width of the display in pixels."""
        if ((self._rotation // 90) & 0x1) == 0x1:  # if rotation index is odd
            return self._height
        return self._width

    @property
    def height(self):
        """The height of the display in pixels."""
        if ((self._rotation // 90) & 0x1) == 0x1:  # if rotation index is odd
            return self._width
        return self._height

    @property
    def rotation(self):
        """
        The rotation of the display.

        :return: The rotation of the display.
        :rtype: int
        """
        return self._rotation

    @rotation.setter
    def rotation(self, value):
        """
        Sets the rotation of the display.

        :param value: The rotation of the display.
        :type value: int
        """

        if value % 90 != 0:
            value = value * 90

        if value == self._rotation:
            return
        
        self._rotation_helper(value)

        self._rotation = value

        if self._touch_device is not None:
            self._touch_device.rotation = value

        self.init()

    @property
    def touch_device(self):
        """
        The associated touch_device.

        :return: The touch_device.
        :rtype: object
        """
        return self._touch_device

    @touch_device.setter
    def touch_device(self, value):
        """
        Sets the touch_device.

        :param value: The touch_device.
        :type value: object
        """
        if hasattr(value, "rotation") or value is None:
            self._touch_device = value
        else:
            raise ValueError("touch_device must have a rotation attribute")
        self._touch_device.rotation = self.rotation

    def fill(self, color):
        """
        Fill the display with a color.

        :param color: The color to fill the display with.
        :type color: int
        """
        self.fill_rect(0, 0, self.width, self.height, color)
        return Area(0, 0, self.width, self.height)

    def scroll(self, dx, dy):
        """
        Scroll the display.

        :param dx: The x-coordinate to scroll.  Not supported.
        :type dx: int
        :param dy: The y-coordinate to scroll.
        :type dy: int
        """
        if dy != 0:
            if self._vssa is not None:
                self.vscsad(self._vssa + dy)
            else:
                self.vscsad(dy)
        if dx != 0:
            raise NotImplementedError("Horizontal scrolling not supported")

    def disable_auto_byte_swap(self, value):
        """
        Disable byte swapping in the display driver.

        If self.requires_bus_swap and the guest application is capable of byte swapping color data
        check to see if byte swapping can be disabled in the display bus.  If so, disable it.

        Guest applications that are capable of byte swapping should include:

            # If byte swapping is required and the display driver is capable of having byte swapping disabled,
            # disable it and set a flag so we can swap the color bytes as they are created.
            if display_drv.requires_byte_swap:
                needs_swap = display_drv.disable_auto_byte_swap(True)
            else:
                needs_swap = False

        :param value: Whether to disable byte swapping in the display bus.
        :type value: bool
        :return: True if the bus swap was disabled, False if it was not.
        :rtype: bool
        """
        if self._requires_byte_swap:
            self._auto_byte_swap_enabled = not value
        else:
            self._auto_byte_swap_enabled = False
        print(f"{self.__class__.__name__}:  auto byte swapping = {self._auto_byte_swap_enabled}")
        return not self._auto_byte_swap_enabled

    @property
    def requires_byte_swap(self):
        """
        Whether the display requires byte swapping.

        :return: Whether the display requires byte swapping.
        :rtype: bool
        """
        return self._requires_byte_swap

    ############### Common API Methods, sometimes overridden ################

    def vscrdef(self, tfa, vsa, bfa):
        """
        Set the vertical scroll definition.  Should be overridden by the
        subclass and called as super().vscrdef(tfa, vsa, bfa).

        :param tfa: The top fixed area.
        :type tfa: int
        :param vsa: The vertical scrolling area.
        :type vsa: int
        :param bfa: The bottom fixed area.
        :type bfa: int
        """
        if tfa + vsa + bfa != self.height:
            raise ValueError(
                "Sum of top, scroll and bottom areas must equal screen height"
            )
        self._tfa = tfa
        self._vsa = vsa
        self._bfa = bfa

    def vscsad(self, vssa=None):
        """
        Set the vertical scroll start address.  Should be overridden by the
        subclass and called as super().vscsad(y).

        :param y: The vertical scroll start address.
        :type y: int
        """
        if vssa is not None:
            self._vssa = vssa
        else:
            return self._vssa

    def _rotation_helper(self, value):
        """
        Helper function to set the rotation of the display.

        :param value: The rotation of the display.
        :type value: int
        """
        # override this method in subclasses to handle rotation
        pass

    ############### Empty API Methods, must be overridden if applicable ################

    @property
    def power(self):
        return -1

    @power.setter
    def power(self, value):
        return

    @property
    def brightness(self):
        return -1

    @brightness.setter
    def brightness(self, value):
        return

    def invert_colors(self, value):
        return

    def reset(self):
        return

    def hard_reset(self):
        return

    def soft_reset(self):
        return

    def sleep_mode(self, value):
        return

    def deinit(self):
        return
    
    def show(self, *args, **kwargs):
        return