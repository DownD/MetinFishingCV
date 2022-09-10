from setuptools import setup

setup(name="MetinFishingCV",
      version='0.1',
      packages=['MetinFishingCV'],
      package_data={'resources': ['resources/*.png']},
      entry_points={
          'console_scripts': [
              'metinfishingbot = MetinFishingCV.FishingBot:main',
              'metinfishingcv = MetinFishingCV.FishingDetection:main'
          ],
      }
      )
