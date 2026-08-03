from opencae.model.entities.profiles.factory import create_profile
from opencae.model.entities.profiles.calculations import profile_properties

def test_extended_profile_types_are_typed():
    assert create_profile('C-profile',name='C').profile_type=='C-profile'
    assert create_profile('U-profile',name='U').profile_type=='U-profile'
    assert create_profile('H-profile',name='H').profile_type=='H-profile'
    assert create_profile('Circle',name='O').profile_type=='Circle'

def test_graph_profile_uses_segment_thickness():
    thin=profile_properties('Graph profile',{'nodes':'1,0,0\n2,10,0','segments':'1,2,1'})
    thick=profile_properties('Graph profile',{'nodes':'1,0,0\n2,10,0','segments':'1,2,2'})
    assert thick['Area']==2*thin['Area']
