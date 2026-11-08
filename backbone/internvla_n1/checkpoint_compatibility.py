"""Exact extras in the released checkpoint unused by the official inference path."""
# The official depth_anything_v2/dinov2.py comments out mask_token registration.
# NavDP calls get_intermediate_layers(), whose token preparation uses masks=None.
# These two entries are ignored by upstream from_pretrained too; no active model
# parameter may be missing, and no other unexpected entry is accepted.
UNUSED_MASK_TOKENS = frozenset({
    'model.navdp.rgbd_encoder.depth_model.mask_token',
    'model.navdp.rgbd_encoder.rgb_model.mask_token',
})


def loading_errors(info):
    return {
        'missing_keys': info.get('missing_keys', []),
        'unexpected_keys': sorted(set(info.get('unexpected_keys', [])) - UNUSED_MASK_TOKENS),
        'mismatched_keys': info.get('mismatched_keys', []),
        'error_msgs': info.get('error_msgs', []),
    }
