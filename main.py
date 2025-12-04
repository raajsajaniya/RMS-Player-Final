name: Build APK
    on: [push, workflow_dispatch]

    jobs:
      build:
        runs-on: ubuntu-20.04

        steps:
          - name: Checkout Code
            uses: actions/checkout@v3

          - name: Setup Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.9'

          - name: Install Dependencies
            run: |
              sudo apt-get update
              sudo apt-get install -y build-essential git ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev libssl-dev libffi-dev unzip autoconf automake libtool

          - name: Install Buildozer
            run: |
              pip install --upgrade pip
              pip install buildozer cython==0.29.33

          - name: Build APK
            run: |
              yes | buildozer android debug

          - name: Upload Artifact
            uses: actions/upload-artifact@v4
            with:
              name: RMS_Player_APK
              path: bin/*.apk
