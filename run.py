from belphegor import utils
from belphegor.utils import data_type, config, token
import logging

#==================================================================================================================================================

if __name__ == "__main__":
    belphybot = data_type.Belphegor(owner_id=config.OWNER_ID)
    belphybot.run(token.TOKEN)
