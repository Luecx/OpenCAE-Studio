from opencae.store.json_patch import apply,changes

def test_reversible_patch_stores_only_changed_branch():
    before={'parts':[{'name':'A','mesh':{'nodes':[1,2,3]}}],'name':'P'}
    after={'parts':[{'name':'B','mesh':{'nodes':[1,2,3]}}],'name':'P'}
    patch=changes(before,after)
    assert len(patch)==1
    assert apply(before,patch,True)==after
    assert apply(after,patch,False)==before
