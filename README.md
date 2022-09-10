# MetinFishingCV 
A computer vision bot for the mini fishing game in metin2.
It uses mainly OpenCV and an Arduino to send mouse commands.
![Preview](/preview.gif)



# Introduction
Inside this game (Metin2) there is a small [mini-game](https://en-wiki.metin2.gameforge.com/index.php/Fishing) that requires the user to click on a small fish 3 times while it moves arround the screen, this fish can only be catched while it is inside a circle.

This project automatizes this flow and allows to use an arduino to send input data.
Using a Ryzen 5 3600 the process of the image took arround 20ms mssing only arround 10% of the clicks.

THIS IS ONLY FOR EDUCATIONAL PURPOSES
# How does it work
This module uses computer vision, by analyzing the images of a specific window or video and detects the position of the fish on screen and whenever the user needs to press the mouse key, after that it will send a serial message to an Arduino Leonardo that will simulate an HID device (a mouse) that's sends a click to the required delta position.

## FishingDetection
This is the module responsible for analyzing the current frame.
It will take a frame and will do the following analysis:
1. Check if the mini-game window is open.
It uses [MatchTemplate](https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html) to search for best location of the reference image (```resources/template_fish_game_border.png```) in the current frame, if the correlation is higher then 0.7 (```GAME_THRESHOLD```) the mini-game is considered open otherwise the mini-game is considered not running and returns.
In order to improve this detection correlation and speed, the frame and reference are downsampled by a ratio value, default is 0.5, (this will increase the speed of the matching in arround 4x), a [BilateralFilter]('https://www.geeksforgeeks.org/python-bilateral-filtering/') is applied to the frame and the resource image to improve the accuracy and finally both images are converted into a gray color scheme.

2. Detect if the fish can be clickable
This is done by cropping the original frame where the mini-game was detected, getting a mask from the application of a color range filter and finally counting the number of positive values in the mask, if there are more then 40.000 (```GRAB_THRESHOLD_SUM```) the fish can be clicked otherwise the fish cannot be clicked.

3. Detect location of the fish
This is done by cropping the original frame where the mini-game was detected, getting a mask from the application of a color range filter then finding the contours of all objects in the mask, and finally grabbing the one with bigger area and getting it's location and bounding box size.



## Arduino Leonardo mouse simulator (SerialHandler)
It is used to send mouse clicks and movement to the computer.
It can be usefull in case the game doesn't register inputs by [pydirectinput](https://github.com/learncodebygaming/pydirectinput).
It uses a very simple and unfinished custom protocol to send data to serial. This protocol was only implemented from the PC to Arduino and not the other way arround but the arduino still communicates with the computer by serial but is just for sending text debug data.
The messaged sent by the python module follow a specific packet structure (More information found on the file ```Arduino/leonardo_mouse_relay.ino```), currently it only supports mouse movement and mouse clicks, the mouse movement, expressed in x,y delta values, needs to be relative to the current position.

## FishingBot
This is the main module that will make use of all other modules and automate the tasks.
Uses [dxCam](https://github.com/ra1nty/DXcam) to grab realtime frames of a specific window.
It has 2 modes of operation, one synchronous where each frame is grabbed and processed sequentially (```--fast```) needs to be specified in the arguments) and one asynchronous where it uses 2 different threads, one to grab the frame and show in a new window and another one to process the detection and every interaction with the game.
There is a kind of state machine to keep track of the current state of the fishing game, each state as a respective action function that is executed on each run and also a timeout and timeout action function that is executed if the timeout is reached.
There are 3 states: 
- ```PULLING_ROD```:
If the fishing game is detected it will change the state to ```SEARCHING_FISH```.
Else it will sleep for a short amount of time and will send the hotkeys ('1' and 'space') trough [pydirectinput](https://github.com/learncodebygaming/pydirectinput), needed by the game to start fishing game, and finally will change the state to ```SEARCHING_FISH```.
- ```SEARCHING_FISH```:
If the fishing game is not detected it will change the state to ```PULLING_ROD```.
Else and if the fish can be clicked it will send a command to the Arduino Leonardo to move the mouse to the specified location and click on it. (This beahviour can be changed to use [pydirectinput](https://github.com/learncodebygaming/pydirectinput), and finally will change the state to ```WAIT_AFTER_CLICK```.
- ```WAIT_AFTER_CLICK```
Sleeps for 1 second.

This states's action functions are called on every frame grabbed by [dxCam](https://github.com/ra1nty/DXcam). 

# How to run

Install Package
```shell
pip install .
```

## Arduino Leonardo
If you want to use the Arduino Leonardo, connect it trough a USB port and upload ```Arduino/leonardo_mouse_relay.ino```.
Whenever executing metinfishingbot the flag ```--use_arduino``` neeeds to be passed.


## Diferent run methods
Display the vision of the bot from the example video in a new window
```shell
metinfishingcv --video video_samples\\fishing_data_test.mp4 --debug
```

Display the vision of the bot only for the fish
```shell
metinfishingcv --video video_samples\\fishing_data_test.mp4
```

Run the bot on the window "Metin" and display it's vision
```shell
metinfishingbot Metin
```

Run the bot, using an arduino for mouse simulation, on the window "Metin" and display it's vision
```shell
metinfishingbot Metin --use_arduino
```

Run the bot on the window "Metin" synchronously without displaying the image and resize the frame to 0.7 
```shell
metinfishingbot Metin --fast --resize_factor 0.7
```