import copy,json,sys
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db';sys.path[:0]=[str(R/'scripts'),str(R/'tests')]
import test_target_media_recovery as t
s=t.full_fixture();p=t.PAYLOAD['campaigns'][0];ids=t.G['ids']
print('fake final flow setup only')
