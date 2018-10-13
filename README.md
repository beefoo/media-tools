# Sort Media

A simple set of scripts that extracts samples from arbitrary media, sorts them, then recombines them. For example, this will sort an audio file by frequency:

```
python run.py -in audio/sample/sonata.mp3 -sort hz -uid sonata -out output/sort_sonata_hz.mp3
```

`sort` can be one of: [tsne](https://lvdmaaten.github.io/tsne/), hz, power, dur

Currently supports `.wav`, `.mp3`, `.mp4`
