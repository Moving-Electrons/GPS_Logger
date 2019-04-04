# GPS Logger using CircuitPython

This is a standalone GPS logger built using Adafruit and Particle hardware. Code is in CircuitPython 4.x.

## Features

- Fully standalone GPS tracker ( not cell phone assisted).
- Location data is recorded to a micro SD card.
- Integrated screen showing basic location information.
- GPS coordinates are recorded only if the position changes by a certain predefined number of degrees. That way, we don’t end up with hundreds of recorded points for the same location if the device doesn’t move for a long period of time.
- **Battery lasts for around 70 hrs. on a single charge**. Also, it keeps working while charging.
- Integrated rechargeable battery (micro USB connector). It can be charged by pretty much any USB port or portable battery pack.
- GPS module sensitive enough to work indoors most of the time.
Bluetooth BLE ready. However, this functionality is not used on this version.

For further information on hardware components and build process, read [this article](http://www.movingelectrons.net/blog/2019/04/03/Building-a-GPS-Logger-with-CircuitPython.html) or search for it in [www.movingelectrons.net](http://www.movingelectrons.net/)