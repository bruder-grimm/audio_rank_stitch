# Audio Rank Stitch - The code behind "Answering Machine, 2026" 
### Art and Code by Christoph Zeckel and Marvin Grimm (Equal Contribution)

This is the repository that holds all code and the questions for "Answering Machine".

If you want to replicate/use this, additional hardware is required:
- We use stereo channels to drive the handset and room speaker arrangement at the same time from one machine without the need for additional soundcards
- Therefore, you will need a mono phone and a mono speaker arrangement
- A CRT is highly recommended

### Usage
- Install using pip and run the package or simply run main.py
- 2 Flask servers will be started on ports 1234 and 5678
  - 1234 will be your user facing recording frontend
  - 5678 is the administrative playback frontend
 
### Info
- As long as you have enough storage you can run this indefinitely


### Acknowledgments
- Christian Steinmetzes for [Pyloudnorm](https://www.christiansteinmetz.com/projects-blog/pyloudnorm)
- Gdaliy Garmiza for [audiocomplib](https://github.com/Gdalik/audiocomplib)
