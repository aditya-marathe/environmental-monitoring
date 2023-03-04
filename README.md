  
# Environmental Monitoring

Coursework for the *Physics Group Project* university module.

The project aims to create an environmental monitoring system using a Raspberry Pi 3B with the Enviro+ Monitor. 

## Setting up Rasbperry Pi
> **Note:** You may also use the preset Rasberry Pi Image avalible on our repository to skip setup. However, please note that *the image may not be up-to-date*.

1. To start, we want to flash an image of the Raspbian operating system (OS) on an micro SD card. The simplest way to achieve this is by  installing the Raspberry Pi Imager from their official website's [downloads page](https://www.raspberrypi.com/software/).
> **Note:** Balena Etcher is another popular alternative, but for this you will have to manually install the most up-to-date image of Raspbian from the downloads page (link provided above). This tutorial will only be covering how to use Raspberry Pi imager.
2. After installation, "allow the app to make changes to your device" and you should see the following window on your screen.

<img src="./Screenshots/DetailedSteps/1.png" width="300">

3. Click on "Choose OS" and select "Raspberry Pi OS (32-bit)". This installs the latest version of Raspbian (or Debian, a Linux-based OS).

<img src="./Screenshots/DetailedSteps/2.png" width="300">

4. Using an micro SD card reader, connect your micro SD card to your computer - you should see a notification from your computer if a storage device was connected. Remember the location (or direcotry) of the micro SD card e.g., "E" or "D" drive.
5. Next, click "Choose Storage" and select the directory of your micro SD card. 

<img src="./Screenshots/DetailedSteps/3.png" width="300">

6. Click the settings icon which has now appeared in the bottom right hand corner. You may set your own hostname, but for this tutorial we will use the hostname "monitor1.local".

<img src="./Screenshots/DetailedSteps/4.png" width="300">

> **Note:** The next 2 steps
7. Check the "Enable SSH" option and select "Use password authentication" which uses the device's password to authenticate an SSH connection. SSH or Secure Shell, is a protocol which allows us to securely connect to our Raspberry Pi via a network connection.

<img src="./Screenshots/DetailedSteps/5.png" width="300">

8. Next, set up a **memorable** password for your device - we will be using the default username "pi".

<img src="./Screenshots/DetailedSteps/6.png" width="300">

9. Finally, check these settings are enabled in the "Presistent settings". At the time of writing, we had difficulties writing to the SD card when "Eject media when finished" was enabled, so we reccommend to keep this disabled.

  <img src="./Screenshots/DetailedSteps/7.png" width="300">

 10. Go back to main page and click on "Write" and click "Yes" on the popup.

  <img src="./Screenshots/DetailedSteps/8.png" width="300">

10. The writing and verification process should take a few minutes.

  <img src="./Screenshots/DetailedSteps/9.png" width="300">

  <img src="./Screenshots/DetailedSteps/10.png" width="300">

11. 


## Project Contributors
- Core team:
	- Chenxi Feng
	- Maya Jagpal
	- Juliette Keller
	- Ruiming Liu
	- Daniel Maguire
	- Aditya Marathe
	- Maj Mis
	- Emi Shindate
	- Celia Yuan

- Project supervisor:
	- Paul Bartlett
