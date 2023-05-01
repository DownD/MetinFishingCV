from setuptools import find_packages, setup

setup(name="MetinFishingCV",
      version='0.1',
      packages=find_packages(),
      package_data={'resources': ['resources/*.png']},
      entry_points={
          'console_scripts': [
              'metinfishingbot = MetinFishingCV.FishingBot:main',
              'metinfishingcv = MetinFishingCV.FishingDetection:main'
          ],
      }
      )
