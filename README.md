# Media tools

_(under construction)_

A set of scripts that extracts samples from arbitrary media, extracts features from those samples, and recombines them in various ways. For example, this will sort an audio file by frequency:

```
python sort_audio.py -in "media/sample/sonata.mp3" -sort "hz=asc" -out "output/sonata_sorted_by_hz.mp3"
```

Where `sort` can be one of: [tsne](https://lvdmaaten.github.io/tsne/) (spectral similarity), `hz` (frequency), `power` (volume), `clarity` (clear harmonic bands), `dur` (clip duration)

## Requirements

Not all of these are required for individual scripts, but covers what's needed for most workflows.

- [Python](https://www.python.org/) (I developed using 3.6, so 3.6+ is recommended and may not work with 2.7+)
- [SciPy](https://www.scipy.org/) for math functions (probably already installed)

### Working with video

- [FFmpeg and FFprobe](https://www.ffmpeg.org/) for working with media files
- [Pillow](https://pillow.readthedocs.io/en/stable/) for image/frame generation
- [MoviePy](https://zulko.github.io/moviepy/) for programmatic video editing
- [PyOpenCL](https://mathema.tician.de/software/pyopencl/) for GPU-accelerated image processing

### Working with audio

- [LibROSA](https://librosa.github.io/librosa/) for audio analysis
- [Pydub](http://pydub.com/) for audio manipulation
- [SoX](http://sox.sourceforge.net/) and [pysndfx](https://pypi.org/project/pysndfx/) for audio effects like reverb

### Misc

- [scikit-learn](https://scikit-learn.org/stable/) for statistics and machine learning features (e.g. TSNE, clustering, classification)
- [Multicore-TSNE](https://github.com/DmitryUlyanov/Multicore-TSNE) for faster TSNE
- [RasterFairy](https://github.com/Quasimondo/RasterFairy) for transforming point cloud to grid
- [Requests](http://docs.python-requests.org/en/master/) for making remote web requests for scraping metadata
- [Curl](https://curl.haxx.se/) for binary downloads

## Large collection workflow

The scripts in this repository were mostly designed for analyzing/visualizing very large collections of media. Here's an example workflow:

### 1. Metadata retrieval

Download all movie metadata from Internet Archive that are in the [Fedflix collection](https://archive.org/details/FedFlix) and created by the [National Archives](https://archive.org/details/FedFlix?and[]=creator%3A%22national+archives+and+records+administration%22) and save to CSV file:

```
python scrapers/internet_archive/download_metadata.py \
-query " collection:(FedFlix) AND mediatype:(movies) AND creator:(national archives and records administration)" \
-out "tmp/ia_fedflixnara.csv"
```

By default, the above script will look for the largest .mp4 asset and associate it with the `filename` property. You can change this format by adding a flag, e.g. `-format .mp3`. If each record has multiple assets associated with it, add a flag `-multi` and each asset with the indicated format will be retrieved and saved as its own row (the record metadata will be the same, except for `filename`)

For details on how to construct a search query, visit the [Internet Archive's advanced search page](https://archive.org/advancedsearch.php).

### 2. Asset download

Next, you can download the assets from each of the movies retrieved from the previous step. You can add a flag to indicate how many parallel downloads to run, e.g. `-threads 3`. Make sure output directory has plenty of space. This particular collection has a 100GB+ of files.

```
python scrapers/internet_archive/download_media.py \
-in "tmp/ia_fedflixnara.csv" \
-out "tmp/downloads/ia_fedflixnara/"
```

### 3. File features

Then retrieve the file features: video duration, has audio track, has video track. By default, it opens the file to get an accurate duration. You can speed this up by just looking at the metadata (less accurate) by adding flag `-fast`.

```
python get_file_features.py \
-in "tmp/ia_fedflixnara.csv" \
-dir "tmp/downloads/ia_fedflixnara/"
```

Note that checking for an audio track doesn't guarantee to catch all silent films since some video files may have a silent audio track. These cases will be captured in the next step.

### 4. Audio analysis

Now we analyze each movie file's audio track for "samples." These essentially are clips of audio that have a distinct [onset](https://en.wikipedia.org/wiki/Onset_(audio)) and release. This could be thought of as a distinct sonic "pulse" or syllable in the case of speech. The `-features` flag adds an analysis step that looks for each sample's volume (`power`) and pitch (`hz` or frequency.) `note` and `octave` are added for convenience, and the `clarity` feature attempts to measure how distinct a particular note is (i.e. very clear harmonic bands.) Samples with high clarity values should be good candidates for musical notes.

```
python audio_to_samples.py \
-in "tmp/ia_fedflixnara.csv" \
-dir "tmp/downloads/ia_fedflixnara/" \
-out "tmp/sampledata/ia_fedflixnara/%s.csv" \
-features
```

The above command will save _all_ samples to .csv files, where each media file will have one .csv file with its respective sample data. Each .csv file will have the same filename as the media source's filename. This will take a long time for large collections.

### 5. Audio analysis metadata

Next we will update the original metadata .csv file with metadata about the samples per file, e.g. number of samples, median volume, median pitch. This will help identify which movies are silent or have unusable audio, e.g. if a file has few samples or its `medianPower` is very low.

```
python get_sample_features.py \
-in "tmp/ia_fedflixnara.csv" \
-dir "tmp/sampledata/ia_fedflixnara/"
```

### 6. Audio analysis

Optionally, you can view the stats of the samples you created:

```
python stats_histogram.py \
-in "tmp/ia_fedflixnara.csv" \
-plot "duration,samples,medianPower,medianHz,medianClarity,medianDur"

python stats_totals.py -in "tmp/ia_fedflixnara.csv"
```

Or view more detailed stats of an individual file's samples:

```
python stats_histogram.py -in "tmp/sampledata/ia_fedflixnara/gov.archives.111-tv-221.mp4.csv"
```

Or view two properties as a scatter plot:

```
python stats_plot.py \
-in "tmp/sampledata/ia_fedflixnara/gov.archives.111-tv-221.mp4.csv" \
-props "power,hz"
```

### 7. Visualizing audio/video

Create a subset by taking all films with more than 500 samples with sound; take the 16,384 (128x128) samples with most power and clarity; limit 100 samples per film

```
python samples_subset.py \
-in "tmp/ia_fedflixnara.csv" \
-dir "tmp/sampledata/ia_fedflixnara/" \
-out "tmp/ia_fedflixnara_subset.csv" \
-filter "samples>500&medianPower>0.5" \
-lim 16384 -ffilter "octave>1&power>0" \
-fsort "power=desc=0.75&clarity=desc" \
-flim 100
```

If the resulting subset is too small, try to modify the `-filter` query and decrease the thresholds for filtering. Typically you'd want to have as small of a `-flim` (sample limit per file) value as you can if you want to have a relatively diverse set of samples.

Now we can attempt to sort this subset be spectral similarity via [t-SNE](https://en.wikipedia.org/wiki/T-distributed_stochastic_neighbor_embedding). First, we must extract 1-D tsne values from the subset and cache the feature data:

```
python samples_to_tsne.py \
-in "tmp/ia_fedflixnara_subset.csv" \
-dir "tmp/sampledata/ia_fedflixnara/" \
-components 1 \
-prefix "stsne" \
-angle 0.1 \
-cache "tmp/ia_fedflixnara_subset_features.p"
-threads 4
```

You can tweak the number of parallel processes (`-threads`) to work best with your processor.

Then sort the samples by t-SNE and output to audio file:

```
python3 features_to_audio.py \
-in "tmp/ia_fedflixnara_subset.csv" \
-dir "tmp/sampledata/ia_fedflixnara/" \
-sort "stsne=asc" \
-out "output/ia_fedflixnara_sort_stsne_asc.mp3"
```

In the resulting audio file, you should hear clear "clusters" of similar-sounding audio.

Now we will lay out the samples on a 2-D grid using t-SNE again, but with two components instead of one. This should be faster if you cached the features in the previous section.

```
python samples_to_tsne.py \
-in "tmp/ia_fedflixnara_subset.csv" \
-dir "tmp/downloads/ia_fedflixnara/" \
-components 2 \
-angle 0.2 \
-cache "tmp/ia_fedflixnara_subset_features.p"
-threads 4
```

Then put the sample subset in a 128x128 grid based on the t-SNE features (essentially created a matrix of samples organized by spectral similarity). This requires [rasterfairy](https://github.com/Quasimondo/RasterFairy) and Python 2.7+

```
python samples_to_grid.py \
-in "tmp/ia_fedflixnara_subset.csv" \
-grid "128x128"
```

Before we visualize the grid, I like to run this script as well:

```
python samples_to_vsamples.py \
-in "tmp/ia_fedflixnara_subset.csv" \
-dir "tmp/downloads/ia_fedflixnara/"
```

The above script is optional and mostly for aesthetic purposes. It analyzes the video component of the audio samples that we extracted from previous steps to extend the sample duration so we're not seeing too much flickering. For example, if an extracted audio sample was only 100 milliseconds, if we loop that, it would be visually flickering and overwhelming. Or, a sample might start right before a new visual scene starts. This script attempts to extend the sample to about a second if it doesn't see a new scene start and attempts to end the sample before a new scene starts. The result adds two columns `vstart` and `vdur` to our input sample data file.

Finally we can generate a visualization. All of the different visualizations are in the `./compositions/` folder. We can start with a simple one:

```
python compositions/proliferation.py \
-in "tmp/ia_fedflixnara_subset.csv" \
-dir "tmp/downloads/ia_fedflixnara/" \
-out "output/ia_fedflixnara_proliferation.mp4" \
-cache \
-cd "tmp/ia_fedflixnara_cache/" \
-ckey "ia_fedflixnara_proliferation" \
-outframe "tmp/ia_fedflixnara_proliferation_frames/frame.%s.png"
```

This script simply plays the samples starting from the center, then outward. When you first run this, it will take a long time since it does some preprocessing which it caches, so it will be faster for subsequent commands. Here's what the script will do, in order:

1. Construct the audio component of the visualization by layering each source audio file as a separate track. This will result in an .mp3 file in the output directory.
2. Analyze the sequence to calculate the maximum size (width/height) of each clip. The result will be cached in the cache directory (`-cd`).
3. Each frame from each clip will be extracted from the source video and cached in the cache directory.
4. Then each frame of the result video is processed and saved to the `-outframe` folder. You can speed this up by adding parallel processing (`-threads`).
5. Finally, the frames and the audio file is compiled to a video file using ffmpeg

_more soon..._
