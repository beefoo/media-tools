# 12 x 24

This is a subset of scripts that is a part of my [larger personal code repository](https://github.com/beefoo/media-tools) of media processing scripts. These scripts are specifically related to a project called [12 x 24](http://brianfoo.com/12x24/) that visualizes the lives of 12 people from 12 different countries over the course of 24 continuous hours using footage from the [Global Lives Project](https://globallives.org/).

[The requirements](https://github.com/beefoo/media-tools#requirements) are the same as those in the parent repository.  All the scripts should be run from the root of this repository.  Here is my workflow for producing the [final film](http://brianfoo.com/12x24/):

### Download all the video assets from the Internet Archive:

```
python3 scrapers/internet_archive/download_media.py \
-in "projects/global_lives/data/ia_globallives_subset.csv" \
-out "media/downloads/ia_globallives/"
```

This will take a pretty long time and depending on your internet connection.

You can modify the input .csv file to adjust which videos you want to download. The current subset was generated from the [projects/global_lives/subset.py](https://github.com/beefoo/media-tools/blob/master/projects/global_lives/subset.py) script which just includes the collections (in the [ia_global_lives_collections.csv](https://github.com/beefoo/media-tools/blob/master/projects/global_lives/data/ia_globallives_collections.csv) file) marked as active.

### Get duration of videos

If you did not change the [video subset file](https://github.com/beefoo/media-tools/blob/master/projects/global_lives/data/ia_globallives_subset.csv), you can skip this step since I already ran this analysis for the current video subset.

```
python3 get_file_features.py \
-in "projects/global_lives/data/ia_globallives_subset.csv" \
-dir "media/downloads/ia_globallives/"
```

### Inspect the collection

Optionally, you can take visualize the collection in a couple of ways. First, you can visually check to see if there's any "gaps" in footage by running:

```
python3 projects/global_lives/viz.py -in "projects/global_lives/data/ia_globallives_subset.csv"
```

Or print out where the gaps are in text format:

```
python3 projects/global_lives/qa.py -in "projects/global_lives/data/ia_globallives_subset.csv"
```

### Generating the movie

Now you can generate the movie using this command:

```
python3 projects/global_lives/movie.py \
-in "projects/global_lives/data/ia_globallives_subset.csv" \
-dir "media/downloads/ia_globallives/" \
-outframe "tmp/global_lives_frames/frame.%s.png" \
-out "output/global_lives.mp4"
```

This will generate video frames, an audio track (.mp3), then combine them into an .mp4 file. This will likely take days depending on your machine. By default it attempts to use up to 8 processing cores. You can adjust this by adding `-vthreads <number of cores>` to your command. If you don't use multiple cores, this can easily take weeks of processing time.

If you changed the video subset in the previous step, you'll need to re-analyze the films (which I have already done for the default subset.) You can do this by providing update links to your edited collections and videos files:

```
-co "projects/global_lives/data/my_globallives_collections.csv" \
-in "projects/global_lives/data/my_globallives_subset.csv" \
-celldat "projects/global_lives/data/my_globallives_cells.csv"
```

The `my_globallives_cells.csv` will be generated when you run the script, and will be populated by an analysis of the videos in the `my_globallives_subset.csv` and `my_globallives_collections.csv` files. This will take a pretty long time.

Type `python3 projects/global_lives/movie.py -h` for additional options. There are a lot of them. Some significant ones are:

- `-celldur <float>`: (cell duration) indicates the duration in minutes each interval should be. By default it is `3.0` (3-minute intervals.) A value of `15.0` will create a significantly shorter film. Note that if you change this value, you must re-analyze the films (outlined earlier in this section)
- `-ppf <float>`: (pixels per frame) indicates how fast the film should be moving. By default it is 1.0 pixel per frame.
- `-maxtpc <int>`: (max tracks per cell) indicates how many audio tracks should be playing at any given time. By default it is 2.
