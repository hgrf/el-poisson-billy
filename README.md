# El Poisson Billy

El Poisson is yet another hacked Big Mouth Billy Bass. It was a little contribution to Moorea's 2023
music video "[Un effort](https://www.youtube.com/watch?v=xZalNH8_v24)". This particular hack
features a Bluetooth audio sink and motor control via bluetooth. The python GUI is easy to use and
can even connect to Ableton via a virtual MIDI interface, so that the fish's movements can be
programmed as a MIDI track. 

## Setup

Please use ESP-IDF v5.1.1 to build the firmware.

You can set up the python app with:

```sh
python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## References

### Other Billy Bass projects

- https://maker.pro/arduino/projects/how-to-animate-billy-bass-with-bluetooth-audio-source
- https://www.instructables.com/Animate-a-Billy-Bass-Mouth-With-Any-Audio-Source/
- https://www.hackster.io/news/this-mod-turns-big-mouth-billy-bass-into-an-arduino-controlled-platform-for-shenanigans-cac985a04b47
- https://os.mbed.com/cookbook/Big-Mouth-Billy-Bass
- https://gist.github.com/jamesbulpin/f3b20833ab0bf035ae8fd3a69405b222
- https://github.com/TensorFlux/BTBillyBass

