// Images that must be skipped in questionnaires and treated as invalid (-1) preferences.
// Keep this list in sync with tooling that generates automated preferences.
window.skipImages = [
    "images/lambda-0.01/alg-design_episode_000_timestep_02.png",
    "images/lambda-0.01/alg-design_episode_008_timestep_05.png",
    "images/lambda-0.01/alg-design_episode_014_timestep_03.png",
    "images/lambda-0.01/alg-design_episode_015_timestep_03.png",
    "images/lambda-0.01/alg-design_episode_021_timestep_05.png",
    "images/lambda-0.01/alg-design_episode_035_timestep_04.png",
    "images/lambda-0.01/alg-design_episode_035_timestep_06.png",
    "images/lambda-0.01/alg-design_episode_038_timestep_03.png",
    "images/lambda-0.01/alg-design_episode_038_timestep_05.png",
    "images/lambda-0.01/alg-design_episode_045_timestep_05.png",
    "images/lambda-0.01/alg-design_episode_045_timestep_06.png",
    "images/lambda-0.01/alg-design_episode_046_timestep_04.png",
    "images/lambda-0.01/alg-design_episode_046_timestep_06.png",
    "images/lambda-0.01/alg-random_episode_016_timestep_02.png",
    "images/lambda-0.01/alg-random_episode_016_timestep_03.png",
    "images/lambda-0.01/alg-random_episode_016_timestep_04.png",
    "images/lambda-0.01/alg-random_episode_016_timestep_05.png",
    "images/lambda-0.01/alg-random_episode_016_timestep_06.png",
    "images/lambda-0.01/alg-random_episode_020_timestep_01.png",
    "images/lambda-0.01/alg-random_episode_020_timestep_02.png",
    "images/lambda-0.01/alg-random_episode_049_timestep_01.png",
    "images/lambda-0.01/alg-random_episode_049_timestep_02.png",
    "images/lambda-0.01/alg-random_episode_049_timestep_03.png",
    "images/lambda-0.01/alg-random_episode_049_timestep_04.png",
    "images/lambda-0.01/alg-random_episode_049_timestep_05.png",
    "images/lambda-0.01/alg-random_episode_049_timestep_06.png"
];

window.skipImagesSet = new Set(window.skipImages);
