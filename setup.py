from setuptools import setup, find_packages

setup(
    name="buildbot_allura_changehook",
    version="0.1",
    packages=find_packages(),
    
    entry_points="""
        [buildbot.webhooks]
        allura = buildbot_allura_changehook.allura:AlluraEventHandler
    """,
    
    # Metadata
    author="John J. Jordan",
    author_email="jj@jjjordan.io",
    description="BuildBot changehook plugin to support Sourceforge and Allura",
    license="MIT",
    keywords="buildbot sourceforge allura changehook webhook change web hook",
    url="https://github.com/jjjordan/buildbot-allura-changehook",
)
