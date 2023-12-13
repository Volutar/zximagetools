# zximagetools
Tools for manipulating ZX images

* demfm.py - neccesary module

* hfe2udi.py - converts hfe image to udi and back. Possible options:

  --recover: If set, treats even single A1 sync byte as 3*A1 (recovers whole series).
  
  --preserve: If set, doesn't sync 4E gap bytes (and C2 pseudo-sync bytes), thus preserving gap size. Otherwise gap area may grow during conversion.
