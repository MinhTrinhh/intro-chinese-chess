from constants import Force
from .bing import Bing
from .ju import Ju
from .ma import Ma
from .pao import Pao
from .shi import Shi
from .shuai import Shuai
from .xiang import Xiang

FORCE_CLZ = {
    Force.JU: Ju,
    Force.MA: Ma,
    Force.XIANG: Xiang,
    Force.SHI: Shi,
    Force.SHUAI: Shuai,
    Force.PAO: Pao,
    Force.BING: Bing
}
