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
- Storage requirements are around 150mb-300mb per hour during an exhibition
- RAM requirements are around the same

### TODO:
- Conceptually, we want to delete full recordings after the last person has heard them
  - This is not for our ears to hear
- All sound bites that live in memory with a buffered write should have their writes pushed to the blanking period
- I/O, which right now mostly lives consolidated in DiskIO, should get seperated to the respective classes
- An LRU Cache should be used for sound bites so we can technically run this forever
- We already do a form of lifetime tracking for soundbites in the markov chain, so we could also evict old recordings from storage (for the same reason)

The goal would be that this code can run indefinitely without having to be restarted.


### Acknowledgments
- Christian Steinmetzes for [Pyloudnorm](https://www.christiansteinmetz.com/projects-blog/pyloudnorm)
- Gdaliy Garmiza for [audiocomplib](https://github.com/Gdalik/audiocomplib)
