import re


_BASE_PATH = "assets/sounds/"


def _path_to(relpath, l, filename):
    res = f"assets/sounds/{relpath}/{filename}"
    l.append(res)
    return res


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('(.)([a-z])([0-9]+)', r'\1\2_\3', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


class SFX2020:
    _p = "SFX2020"
    _a = []
    access_denied_now                      = _path_to(_p, _a, "AccessDeniedNow.wav")
    attention_voltage                      = _path_to(_p, _a, "AttentionVoltage.wav")
    bad_landing_zone                       = _path_to(_p, _a, "BadLandingZone.wav")
    beat_my_face_nes_style                 = _path_to(_p, _a, "BeatMyFaceNESStyle.wav")
    bot_changing_direction                 = _path_to(_p, _a, "BotChangingDirection.wav")
    break_through_the_wall                 = _path_to(_p, _a, "BreakThroughTheWall.wav")
    bullet_bounce                          = _path_to(_p, _a, "BulletBounce.wav")
    bullet_drop_on                         = _path_to(_p, _a, "BulletDropOn.wav")
    bullet_slam                            = _path_to(_p, _a, "BulletSlam.wav")
    bullet_snappin                         = _path_to(_p, _a, "BulletSnappin.wav")
    catapult_mini_bomb                     = _path_to(_p, _a, "CatapultMiniBomb.wav")
    catch_me_if_you_can                    = _path_to(_p, _a, "CatchMeIfYouCan.wav")
    changing_direction                     = _path_to(_p, _a, "ChangingDirection.wav")
    check_menu_item_2                      = _path_to(_p, _a, "CheckMenuItem2.wav")
    check_menu_item                        = _path_to(_p, _a, "CheckMenuItem.wav")
    circling_power                         = _path_to(_p, _a, "CirclingPower.wav")
    cloning_scanning_unit                  = _path_to(_p, _a, "CloningScanningUnit.wav")
    command_not_available                  = _path_to(_p, _a, "CommandNotAvailable.wav")
    communication_line_ready               = _path_to(_p, _a, "CommunicationLineReady.wav")
    confused_attack_style                  = _path_to(_p, _a, "ConfusedAttackStyle.wav")
    confusing_energy_exchange              = _path_to(_p, _a, "ConfusingEnergyExchange.wav")
    confusing_falling_down                 = _path_to(_p, _a, "ConfusingFallingDown.wav")
    connection_interrupted                 = _path_to(_p, _a, "ConnectionInterrupted.wav")
    construction_ready                     = _path_to(_p, _a, "ConstructionReady.wav")
    coordinates_received                   = _path_to(_p, _a, "CoordinatesReceived.wav")
    crystal_destroy                        = _path_to(_p, _a, "CrystalDestroy.wav")
    data_computed_2                        = _path_to(_p, _a, "DataComputed2.wav")
    data_computed_3                        = _path_to(_p, _a, "DataComputed3.wav")
    data_computed                          = _path_to(_p, _a, "DataComputed.wav")
    data_stored_and_ready                  = _path_to(_p, _a, "DataStoredAndReady.wav")
    definite_hit_2                         = _path_to(_p, _a, "DefiniteHit2.wav")
    definite_hit                           = _path_to(_p, _a, "DefiniteHit.wav")
    definite_missile_launch                = _path_to(_p, _a, "DefiniteMissileLaunch.wav")
    definite_shot_2                        = _path_to(_p, _a, "DefiniteShot2.wav")
    definite_shot_3                        = _path_to(_p, _a, "DefiniteShot3.wav")
    definite_shot_4                        = _path_to(_p, _a, "DefiniteShot4.wav")
    definite_shot_5                        = _path_to(_p, _a, "DefiniteShot5.wav")
    definite_shot                          = _path_to(_p, _a, "DefiniteShot.wav")
    deploying_detector                     = _path_to(_p, _a, "DeployingDetector.wav")
    deploying_special_field_area           = _path_to(_p, _a, "DeployingSpecialFieldArea.wav")
    deploy_sensors_scanning_area           = _path_to(_p, _a, "DeploySensorsScanningArea.wav")
    destroy_monster_2                      = _path_to(_p, _a, "DestroyMonster2.wav")
    destroy_monster                        = _path_to(_p, _a, "DestroyMonster.wav")
    digital_laugh                          = _path_to(_p, _a, "DigitalLaugh.wav")
    digital_rearrange                      = _path_to(_p, _a, "DigitalRearrange.wav")
    direct_attack                          = _path_to(_p, _a, "DirectAttack.wav")
    direct_fire_blade_damage               = _path_to(_p, _a, "DirectFireBladeDamage.wav")
    direct_laser_attack                    = _path_to(_p, _a, "DirectLaserAttack.wav")
    direct_laser_blade_attack              = _path_to(_p, _a, "DirectLaserBladeAttack.wav")
    distance_is_too_far                    = _path_to(_p, _a, "DistanceIsTooFar.wav")
    dont_understand_your_language          = _path_to(_p, _a, "DontUnderstandYourLanguage.wav")
    double_laser_shot                      = _path_to(_p, _a, "DoubleLaserShot.wav")
    double_mega_laser_shot                 = _path_to(_p, _a, "DoubleMegaLaserShot.wav")
    dramatic_hitpoint                      = _path_to(_p, _a, "DramaticHitpoint.wav")
    dramatic_scene_sound                   = _path_to(_p, _a, "DramaticSceneSound.wav")
    drone_fly                              = _path_to(_p, _a, "DroneFly.wav")
    drop_longer                            = _path_to(_p, _a, "DropLonger.wav")
    drop_mini                              = _path_to(_p, _a, "DropMini.wav")
    elastic_shield_attack_2                = _path_to(_p, _a, "ElasticShieldAttack2.wav")
    elastic_shield_attack                  = _path_to(_p, _a, "ElasticShieldAttack.wav")
    electric_attack_direct                 = _path_to(_p, _a, "ElectricAttackDirect.wav")
    electric_attack                        = _path_to(_p, _a, "ElectricAttack.wav")
    electric_defense                       = _path_to(_p, _a, "ElectricDefense.wav")
    electric_field                         = _path_to(_p, _a, "ElectricField.wav")
    electric_gate_power_on                 = _path_to(_p, _a, "ElectricGatePowerOn.wav")
    electric_impression_2                  = _path_to(_p, _a, "ElectricImpression2.wav")
    electric_impression                    = _path_to(_p, _a, "ElectricImpression.wav")
    electricity_short                      = _path_to(_p, _a, "ElectricityShort.wav")
    electricity                            = _path_to(_p, _a, "Electricity.wav")
    end_of_power_short                     = _path_to(_p, _a, "EndOfPowerShort.wav")
    enemy_flying_monster_special_attack    = _path_to(_p, _a, "EnemyFlyingMonsterSpecialAttack.wav")
    energetic_shield                       = _path_to(_p, _a, "EnergeticShield.wav")
    energeting_circling_upload             = _path_to(_p, _a, "EnergetingCirclingUpload.wav")
    energy_changing                        = _path_to(_p, _a, "EnergyChanging.wav")
    energy_decrease_shot                   = _path_to(_p, _a, "EnergyDecreaseShot.wav")
    energy_level_very_low                  = _path_to(_p, _a, "EnergyLevelVeryLow.wav")
    energy_reloaded_to_maximum             = _path_to(_p, _a, "EnergyReloadedToMaximum.wav")
    energy_shield_activated                = _path_to(_p, _a, "EnergyShieldActivated.wav")
    energy_upload_to_max_level_shorter     = _path_to(_p, _a, "EnergyUploadToMaxLevelShorter.wav")
    energy_upload_to_max_level             = _path_to(_p, _a, "EnergyUploadToMaxLevel.wav")
    extra_hit_point                        = _path_to(_p, _a, "ExtraHitPoint.wav")
    extreme_interruption                   = _path_to(_p, _a, "ExtremeInterruption.wav")
    falling_down_again_2                   = _path_to(_p, _a, "FallingDownAgain2.wav")
    falling_down_again_3                   = _path_to(_p, _a, "FallingDownAgain3.wav")
    falling_down_again                     = _path_to(_p, _a, "FallingDownAgain.wav")
    fallin_star_longer                     = _path_to(_p, _a, "FallinStarLonger.wav")
    fallin_star                            = _path_to(_p, _a, "FallinStar.wav")
    fast_monster_sound                     = _path_to(_p, _a, "FastMonsterSound.wav")
    fast_space_ships_beside_me             = _path_to(_p, _a, "FastSpaceShipsBesideMe.wav")
    final_shield_defense                   = _path_to(_p, _a, "FinalShieldDefense.wav")
    fire_burn_out                          = _path_to(_p, _a, "FireBurnOut.wav")
    flip_attack_style                      = _path_to(_p, _a, "FlipAttackStyle.wav")
    following_coordinates                  = _path_to(_p, _a, "FollowingCoordinates.wav")
    force_resource_gathering               = _path_to(_p, _a, "ForceResourceGathering.wav")
    funky_explosion                        = _path_to(_p, _a, "FunkyExplosion.wav")
    funky_laser_attack                     = _path_to(_p, _a, "FunkyLaserAttack.wav")
    galactic_gate_interruption             = _path_to(_p, _a, "GalacticGateInterruption.wav")
    gather_bots_attack_each_other          = _path_to(_p, _a, "GatherBotsAttackEachOther.wav")
    gather_unit_hurt                       = _path_to(_p, _a, "GatherUnitHurt.wav")
    get_a_power_up                         = _path_to(_p, _a, "GetAPowerUp.wav")
    get_extra_energy_level                 = _path_to(_p, _a, "GetExtraEnergyLevel.wav")
    get_the_space_item                     = _path_to(_p, _a, "GetTheSpaceItem.wav")
    get_up_power_item                      = _path_to(_p, _a, "GetUpPowerItem.wav")
    greater_hit                            = _path_to(_p, _a, "GreaterHit.wav")
    happy_uploading_battery                = _path_to(_p, _a, "HappyUploadingBattery.wav")
    hard_rocket_launch                     = _path_to(_p, _a, "HardRocketLaunch.wav")
    heli_ship_langing                      = _path_to(_p, _a, "HeliShipLanging.wav")
    heli_ship_langing_wrong                = _path_to(_p, _a, "HeliShipLangingWrong.wav")
    hit_on_energetic_shield                = _path_to(_p, _a, "HitOnEnergeticShield.wav")
    hit_on_me                              = _path_to(_p, _a, "HitOnMe.wav")
    hit_the_ground                         = _path_to(_p, _a, "HitTheGround.wav")
    i_get_your_power                       = _path_to(_p, _a, "IGetYourPower.wav")
    immediate_laser_attack                 = _path_to(_p, _a, "ImmediateLaserAttack.wav")
    impact_mini                            = _path_to(_p, _a, "ImpactMini.wav")
    impact_on_steel_shield                 = _path_to(_p, _a, "ImpactOnSteelShield.wav")
    impact_on_steel_smooth                 = _path_to(_p, _a, "ImpactOnSteelSmooth.wav")
    insufficient_energy                    = _path_to(_p, _a, "InsufficientEnergy.wav")
    insufficient_time                      = _path_to(_p, _a, "InsufficientTime.wav")
    interference                           = _path_to(_p, _a, "Interference.wav")
    interruption_method_2                  = _path_to(_p, _a, "InterruptionMethod2.wav")
    interruption_method                    = _path_to(_p, _a, "InterruptionMethod.wav")
    interruption                           = _path_to(_p, _a, "Interruption.wav")
    invalid_target                         = _path_to(_p, _a, "InvalidTarget.wav")
    item_selected                          = _path_to(_p, _a, "ItemSelected.wav")
    jump_on_it                             = _path_to(_p, _a, "JumpOnIt.wav")
    just_a_little_coin                     = _path_to(_p, _a, "JustALittleCoin.wav")
    just_a_swish                           = _path_to(_p, _a, "JustASwish.wav")
    laser_attack_mini                      = _path_to(_p, _a, "LaserAttackMini.wav")
    laser_mini_shot                        = _path_to(_p, _a, "LaserMiniShot.wav")
    laser_monster_attack                   = _path_to(_p, _a, "LaserMonsterAttack.wav")
    laser_shot                             = _path_to(_p, _a, "LaserShot.wav")
    little_bit_of_crystal_reward           = _path_to(_p, _a, "LittleBitOfCrystalReward.wav")
    little_falling_down                    = _path_to(_p, _a, "LittleFallingDown.wav")
    little_reward                          = _path_to(_p, _a, "LittleReward.wav")
    long_energetic_refresh                 = _path_to(_p, _a, "LongEnergeticRefresh.wav")
    low_bass_hit                           = _path_to(_p, _a, "LowBassHit.wav")
    mass_gun_shots                         = _path_to(_p, _a, "MassGunShots.wav")
    mech_is_ready                          = _path_to(_p, _a, "MechIsReady.wav")
    mech_movement_ready                    = _path_to(_p, _a, "MechMovementReady.wav")
    mega_missile_launch                    = _path_to(_p, _a, "MegaMissileLaunch.wav")
    mega_upload_power_up                   = _path_to(_p, _a, "MegaUploadPowerUp.wav")
    mine_detected_2                        = _path_to(_p, _a, "MineDetected2.wav")
    mine_detected                          = _path_to(_p, _a, "MineDetected.wav")
    mini_blade_direct_attack               = _path_to(_p, _a, "MiniBladeDirectAttack.wav")
    mini_bot_system_fast_restart           = _path_to(_p, _a, "MiniBotSystemFastRestart.wav")
    mini_bot_systems_ready                 = _path_to(_p, _a, "MiniBotSystemsReady.wav")
    mini_explosion_chain_reaction          = _path_to(_p, _a, "MiniExplosionChainReaction.wav")
    mini_hit_impact_2                      = _path_to(_p, _a, "MiniHitImpact2.wav")
    mini_hit_impact                        = _path_to(_p, _a, "MiniHitImpact.wav")
    mini_hit_nice                          = _path_to(_p, _a, "MiniHitNice.wav")
    mini_hit_point                         = _path_to(_p, _a, "MiniHitPoint.wav")
    mini_hit                               = _path_to(_p, _a, "MiniHit.wav")
    mini_laser_attack_2                    = _path_to(_p, _a, "MiniLaserAttack2.wav")
    mini_laser_attack_3                    = _path_to(_p, _a, "MiniLaserAttack3.wav")
    mini_laser_attack_4                    = _path_to(_p, _a, "MiniLaserAttack4.wav")
    mini_laser_attack                      = _path_to(_p, _a, "MiniLaserAttack.wav")
    minimal_space_warp                     = _path_to(_p, _a, "MinimalSpaceWarp.wav")
    mini_monster_destroy                   = _path_to(_p, _a, "MiniMonsterDestroy.wav")
    mini_rocket_flies_beside_me            = _path_to(_p, _a, "MiniRocketFliesBesideMe.wav")
    mini_shield_attack_2                   = _path_to(_p, _a, "MiniShieldAttack2.wav")
    mini_shield_attack                     = _path_to(_p, _a, "MiniShieldAttack.wav")
    mini_shot_2                            = _path_to(_p, _a, "MiniShot2.wav")
    mini_shot_3                            = _path_to(_p, _a, "MiniShot3.wav")
    mini_shot_4                            = _path_to(_p, _a, "MiniShot4.wav")
    mini_shot                              = _path_to(_p, _a, "MiniShot.wav")
    mini_space_blade_attack                = _path_to(_p, _a, "MiniSpaceBladeAttack.wav")
    missile_beside_me                      = _path_to(_p, _a, "MissileBesideMe.wav")
    missile_burn_out                       = _path_to(_p, _a, "MissileBurnOut.wav")
    missile_fire                           = _path_to(_p, _a, "MissileFire.wav")
    missile_launch_fast                    = _path_to(_p, _a, "MissileLaunchFast.wav")
    missile_launch_mini_2                  = _path_to(_p, _a, "MissileLaunchMini2.wav")
    missile_launch_mini                    = _path_to(_p, _a, "MissileLaunchMini.wav")
    missile_launch                         = _path_to(_p, _a, "MissileLaunch.wav")
    missile_mini                           = _path_to(_p, _a, "MissileMini.wav")
    monster_changing_direction             = _path_to(_p, _a, "MonsterChangingDirection.wav")
    monster_downground_effect              = _path_to(_p, _a, "MonsterDowngroundEffect.wav")
    monster_energy_reload_full             = _path_to(_p, _a, "MonsterEnergyReloadFull.wav")
    monster_energy_reload                  = _path_to(_p, _a, "MonsterEnergyReload.wav")
    monster_goes_wrong_way                 = _path_to(_p, _a, "MonsterGoesWrongWay.wav")
    monster_hit_mini                       = _path_to(_p, _a, "MonsterHitMini.wav")
    monster_movement                       = _path_to(_p, _a, "MonsterMovement.wav")
    monster_runaway                        = _path_to(_p, _a, "MonsterRunaway.wav")
    monster_selected                       = _path_to(_p, _a, "MonsterSelected.wav")
    monster_spike_attack                   = _path_to(_p, _a, "MonsterSpikeAttack.wav")
    monster_unburrow                       = _path_to(_p, _a, "MonsterUnburrow.wav")
    monster_upground_effect                = _path_to(_p, _a, "MonsterUpgroundEffect.wav")
    multiple_interruption_signals          = _path_to(_p, _a, "MultipleInterruptionSignals.wav")
    multiple_laser_attack                  = _path_to(_p, _a, "MultipleLaserAttack.wav")
    multi_power_up_grade                   = _path_to(_p, _a, "MultiPowerUpGrade.wav")
    multi_upload                           = _path_to(_p, _a, "MultiUpload.wav")
    my_shield_is_stronger                  = _path_to(_p, _a, "MyShieldIsStronger.wav")
    new_ability_or_upgrade_available       = _path_to(_p, _a, "NewAbilityOrUpgradeAvailable.wav")
    new_hit_point                          = _path_to(_p, _a, "NewHitPoint.wav")
    no_more_power_robot                    = _path_to(_p, _a, "NoMorePowerRobot.wav")
    not_enough_energy                      = _path_to(_p, _a, "NotEnoughEnergy.wav")
    observer_detect_an_important_resource  = _path_to(_p, _a, "ObserverDetectAnImportantResource.wav")
    observer_falling_down                  = _path_to(_p, _a, "ObserverFallingDown.wav")
    observer_found_new_area                = _path_to(_p, _a, "ObserverFoundNewArea.wav")
    observer_new_upgrade_ready             = _path_to(_p, _a, "ObserverNewUpgradeReady.wav")
    observer_power_off_and_dead            = _path_to(_p, _a, "ObserverPowerOffAndDead.wav")
    observer_reporting                     = _path_to(_p, _a, "ObserverReporting.wav")
    observer_runaway_from_enemy            = _path_to(_p, _a, "ObserverRunawayFromEnemy.wav")
    observer_runaway                       = _path_to(_p, _a, "ObserverRunaway.wav")
    observer_select_movement               = _path_to(_p, _a, "ObserverSelectMovement.wav")
    option_select                          = _path_to(_p, _a, "OptionSelect.wav")
    path_finding_bot_wrong_way             = _path_to(_p, _a, "PathFindingBotWrongWay.wav")
    perfect_shield_guard                   = _path_to(_p, _a, "PerfectShieldGuard.wav")
    point_selected                         = _path_to(_p, _a, "PointSelected.wav")
    power_off_short                        = _path_to(_p, _a, "PowerOffShort.wav")
    radio_connection_on                    = _path_to(_p, _a, "RadioConnectionOn.wav")
    recall_teleport_action                 = _path_to(_p, _a, "RecallTeleportAction.wav")
    reloading_machine_is_empty             = _path_to(_p, _a, "ReloadingMachineIsEmpty.wav")
    reload_on_battery                      = _path_to(_p, _a, "ReloadOnBattery.wav")
    reload_rocket_launchers                = _path_to(_p, _a, "ReloadRocketLaunchers.wav")
    robot_found_an_obstacle                = _path_to(_p, _a, "RobotFoundAnObstacle.wav")
    robot_loses_energy                     = _path_to(_p, _a, "RobotLosesEnergy.wav")
    robot_malfunction                      = _path_to(_p, _a, "RobotMalfunction.wav")
    robot_options_select                   = _path_to(_p, _a, "RobotOptionsSelect.wav")
    robot_slide_on_direction_change        = _path_to(_p, _a, "RobotSlideOnDirectionChange.wav")
    rocket_beside_me                       = _path_to(_p, _a, "RocketBesideMe.wav")
    rocket_burn                            = _path_to(_p, _a, "RocketBurn.wav")
    rocket_launch_mini                     = _path_to(_p, _a, "RocketLaunchMini.wav")
    rocket_mini                            = _path_to(_p, _a, "RocketMini.wav")
    rocket_shot                            = _path_to(_p, _a, "RocketShot.wav")
    rocket_smoke                           = _path_to(_p, _a, "RocketSmoke.wav")
    secret_mine_planted                    = _path_to(_p, _a, "SecretMinePlanted.wav")
    select_an_option_2                     = _path_to(_p, _a, "SelectAnOption2.wav")
    select_an_option                       = _path_to(_p, _a, "SelectAnOption.wav")
    select_a_point                         = _path_to(_p, _a, "SelectAPoint.wav")
    select_menu_item_or_hover              = _path_to(_p, _a, "SelectMenuItemOrHover.wav")
    sending_message_outa_space             = _path_to(_p, _a, "SendingMessageOutaSpace.wav")
    sharp_blade_attack                     = _path_to(_p, _a, "SharpBladeAttack.wav")
    shield_defends_bullets                 = _path_to(_p, _a, "ShieldDefendsBullets.wav")
    shield_detected                        = _path_to(_p, _a, "ShieldDetected.wav")
    shield_mini_defend                     = _path_to(_p, _a, "ShieldMiniDefend.wav")
    short_circuit_robot                    = _path_to(_p, _a, "ShortCircuitRobot.wav")
    short_select_button                    = _path_to(_p, _a, "ShortSelectButton.wav")
    short_signal_sound                     = _path_to(_p, _a, "ShortSignalSound.wav")
    shot_me_down                           = _path_to(_p, _a, "ShotMeDown.wav")
    shot_on_a_monster                      = _path_to(_p, _a, "ShotOnAMonster.wav")
    sight_range_increased                  = _path_to(_p, _a, "SightRangeIncreased.wav")
    simple_missile_launch                  = _path_to(_p, _a, "SimpleMissileLaunch.wav")
    simply_target_point                    = _path_to(_p, _a, "SimplyTargetPoint.wav")
    single_shot_2                          = _path_to(_p, _a, "SingleShot2.wav")
    single_shot_3                          = _path_to(_p, _a, "SingleShot3.wav")
    single_shot_4                          = _path_to(_p, _a, "SingleShot4.wav")
    single_shot                            = _path_to(_p, _a, "SingleShot.wav")
    smooth_attack_style                    = _path_to(_p, _a, "SmoothAttackStyle.wav")
    smooth_laser_attack                    = _path_to(_p, _a, "SmoothLaserAttack.wav")
    smooth_weapon_attack                   = _path_to(_p, _a, "SmoothWeaponAttack.wav")
    some_little_spike_hurt_2               = _path_to(_p, _a, "SomeLittleSpikeHurt2.wav")
    some_little_spike_hurt                 = _path_to(_p, _a, "SomeLittleSpikeHurt.wav")
    some_missile_impacted                  = _path_to(_p, _a, "SomeMissileImpacted.wav")
    space_coin_dropped                     = _path_to(_p, _a, "SpaceCoinDropped.wav")
    space_destroy_mini_ship                = _path_to(_p, _a, "SpaceDestroyMiniShip.wav")
    space_gun_fire_2                       = _path_to(_p, _a, "SpaceGunFire2.wav")
    space_gun_fire                         = _path_to(_p, _a, "SpaceGunFire.wav")
    space_gun_reload                       = _path_to(_p, _a, "SpaceGunReload.wav")
    space_heli_arrived                     = _path_to(_p, _a, "SpaceHeliArrived.wav")
    space_obstacle_2                       = _path_to(_p, _a, "SpaceObstacle2.wav")
    space_obstacle                         = _path_to(_p, _a, "SpaceObstacle.wav")
    space_police_is_coming                 = _path_to(_p, _a, "SpacePoliceIsComing.wav")
    space_ship_electric_interference       = _path_to(_p, _a, "SpaceShipElectricInterference.wav")
    space_ship_interruption                = _path_to(_p, _a, "SpaceShipInterruption.wav")
    special_bomb_has_been_planted          = _path_to(_p, _a, "SpecialBombHasBeenPlanted.wav")
    special_mini_reward                    = _path_to(_p, _a, "SpecialMiniReward.wav")
    special_nearly_attack_style            = _path_to(_p, _a, "SpecialNearlyAttackStyle.wav")
    special_reward_reloaded                = _path_to(_p, _a, "SpecialRewardReloaded.wav")
    special_reward_short_2                 = _path_to(_p, _a, "SpecialRewardShort2.wav")
    special_reward_short                   = _path_to(_p, _a, "SpecialRewardShort.wav")
    special_reward                         = _path_to(_p, _a, "SpecialReward.wav")
    special_weapon                         = _path_to(_p, _a, "SpecialWeapon.wav")
    stones_slam_to_the_ground              = _path_to(_p, _a, "StonesSlamToTheGround.wav")
    strange_signal_detected                = _path_to(_p, _a, "StrangeSignalDetected.wav")
    suddenly_falling_down                  = _path_to(_p, _a, "SuddenlyFallingDown.wav")
    suprise_reward_short                   = _path_to(_p, _a, "SupriseRewardShort.wav")
    suprise_reward                         = _path_to(_p, _a, "SupriseReward.wav")
    time_is_out_soon                       = _path_to(_p, _a, "TimeIsOutSoon.wav")
    total_burn_out                         = _path_to(_p, _a, "TotalBurnOut.wav")
    ufo_destroyed_falling_down             = _path_to(_p, _a, "UFODestroyedFallingDown.wav")
    ufo_destroyed                          = _path_to(_p, _a, "UFODestroyed.wav")
    ufo_fly_above_me                       = _path_to(_p, _a, "UFOFlyAboveMe.wav")
    unable_landing_area                    = _path_to(_p, _a, "UnableLandingArea.wav")
    unable_to_gather_resource              = _path_to(_p, _a, "UnableToGatherResource.wav")
    unclear_instructions                   = _path_to(_p, _a, "UnclearInstructions.wav")
    unit_cant_move_on                      = _path_to(_p, _a, "UnitCantMoveOn.wav")
    unit_flip_2                            = _path_to(_p, _a, "UnitFlip2.wav")
    unit_flip                              = _path_to(_p, _a, "UnitFlip.wav")
    unit_loses_energetic_shield            = _path_to(_p, _a, "UnitLosesEnergeticShield.wav")
    units_detect_in_area                   = _path_to(_p, _a, "UnitsDetectInArea.wav")
    unit_selected_with_very_low_power      = _path_to(_p, _a, "UnitSelectedWithVeryLowPower.wav")
    unknown_attak_style                    = _path_to(_p, _a, "UnknownAttakStyle.wav")
    unknown_objects_in_area                = _path_to(_p, _a, "UnknownObjectsInArea.wav")
    unknown_power                          = _path_to(_p, _a, "UnknownPower.wav")
    unknown_shot_style                     = _path_to(_p, _a, "UnknownShotStyle.wav")
    unknown_signal_2                       = _path_to(_p, _a, "UnknownSignal2.wav")
    unknown_signal                         = _path_to(_p, _a, "UnknownSignal.wav")
    unkown_resource_or_enemy_detected      = _path_to(_p, _a, "UnkownResourceOrEnemyDetected.wav")
    unsure_direction_bot_2                 = _path_to(_p, _a, "UnsureDirectionBot2.wav")
    unsure_direction_bot                   = _path_to(_p, _a, "UnsureDirectionBot.wav")
    unsure_select                          = _path_to(_p, _a, "UnsureSelect.wav")
    unusual_coin_reward                    = _path_to(_p, _a, "UnusualCoinReward.wav")
    unusual_reward_sound                   = _path_to(_p, _a, "UnusualRewardSound.wav")
    unusual_shield_detection               = _path_to(_p, _a, "UnusualShieldDetection.wav")
    upload_gun_before_energetic_explosion  = _path_to(_p, _a, "UploadGunBeforeEnergeticExplosion.wav")
    uploading_ready_bot                    = _path_to(_p, _a, "UploadingReadyBot.wav")
    very_massive_energetic_shield_on       = _path_to(_p, _a, "VeryMassiveEnergeticShieldOn.wav")
    very_short_impact                      = _path_to(_p, _a, "VeryShortImpact.wav")
    very_special_item_discovered_2         = _path_to(_p, _a, "VerySpecialItemDiscovered2.wav")
    very_special_item_discovered           = _path_to(_p, _a, "VerySpecialItemDiscovered.wav")
    weapon_launch_mini                     = _path_to(_p, _a, "WeaponLaunchMini.wav")
    wrong_langing_zone                     = _path_to(_p, _a, "WrongLangingZone.wav")
    wrong_way_bot                          = _path_to(_p, _a, "WrongWayBot.wav")


    @staticmethod
    def _assets_to_code():
        """Utility method that gen's the above boilerplate code (not used at runtime).
        """
        file_to_process = "/home/david/Coding/python/circuits/assets/sounds/SFX2020/0_manifest.txt"

        with open(file_to_process) as f:
            lines = f.readlines()
            lines = [line.rstrip() for line in lines]

        tabs = 10

        for l in lines:
            refname = camel_to_snake(l.replace(".wav", ""))
            if len(refname) < tabs * 4 - 2:
                refname += (" " * ((tabs * 4 - 2) - len(refname)))
            print(f"{refname} = _path_to(\"{l}\")")


class ModernUI:

    _p = "Cyberleaf-ModernUISFX/Sounds"
    _a = []  # all sounds

    camera_snapshot                = _path_to(_p, _a, "CameraSnapshot.wav")
    click_and_slide                = _path_to(_p, _a, "ClickAndSlide.wav")
    clicky_button_1a               = _path_to(_p, _a, "ClickyButton1a.wav")
    clicky_button_1b               = _path_to(_p, _a, "ClickyButton1b.wav")
    clicky_button_2                = _path_to(_p, _a, "ClickyButton2.wav")
    clicky_button_3a               = _path_to(_p, _a, "ClickyButton3a.wav")
    clicky_button_3b               = _path_to(_p, _a, "ClickyButton3b.wav")
    clicky_button_4                = _path_to(_p, _a, "ClickyButton4.wav")
    clicky_button_5a               = _path_to(_p, _a, "ClickyButton5a.wav")
    clicky_button_5b               = _path_to(_p, _a, "ClickyButton5b.wav")
    clicky_button_6                = _path_to(_p, _a, "ClickyButton6.wav")
    clicky_button_7                = _path_to(_p, _a, "ClickyButton7.wav")
    clicky_button_8                = _path_to(_p, _a, "ClickyButton8.wav")
    clicky_button_9a               = _path_to(_p, _a, "ClickyButton9a.wav")
    clicky_button_9b               = _path_to(_p, _a, "ClickyButton9b.wav")
    clicky_button_10a              = _path_to(_p, _a, "ClickyButton10a.wav")
    clicky_button_10b              = _path_to(_p, _a, "ClickyButton10b.wav")
    close_or_disable_1             = _path_to(_p, _a, "CloseOrDisable1.wav")
    close_or_disable_2             = _path_to(_p, _a, "CloseOrDisable2.wav")
    close_or_disable_3             = _path_to(_p, _a, "CloseOrDisable3.wav")
    close_or_disable_4             = _path_to(_p, _a, "CloseOrDisable4.wav")
    close_or_disable_5             = _path_to(_p, _a, "CloseOrDisable5.wav")
    error_1                        = _path_to(_p, _a, "Error1.wav")
    error_2                        = _path_to(_p, _a, "Error2.wav")
    error_3                        = _path_to(_p, _a, "Error3.wav")
    error_4                        = _path_to(_p, _a, "Error4.wav")
    error_5                        = _path_to(_p, _a, "Error5.wav")
    generic_button_1               = _path_to(_p, _a, "GenericButton1.wav")
    generic_button_2               = _path_to(_p, _a, "GenericButton2.wav")
    generic_button_3               = _path_to(_p, _a, "GenericButton3.wav")
    generic_button_4               = _path_to(_p, _a, "GenericButton4.wav")
    generic_button_5               = _path_to(_p, _a, "GenericButton5.wav")
    generic_button_6               = _path_to(_p, _a, "GenericButton6.wav")
    generic_button_7               = _path_to(_p, _a, "GenericButton7.wav")
    generic_button_8               = _path_to(_p, _a, "GenericButton8.wav")
    generic_button_9               = _path_to(_p, _a, "GenericButton9.wav")
    generic_button_10              = _path_to(_p, _a, "GenericButton10.wav")
    generic_button_11              = _path_to(_p, _a, "GenericButton11.wav")
    generic_button_12              = _path_to(_p, _a, "GenericButton12.wav")
    generic_button_13              = _path_to(_p, _a, "GenericButton13.wav")
    generic_button_14              = _path_to(_p, _a, "GenericButton14.wav")
    generic_button_15              = _path_to(_p, _a, "GenericButton15.wav")
    generic_notification_1         = _path_to(_p, _a, "GenericNotification1.wav")
    generic_notification_2         = _path_to(_p, _a, "GenericNotification2.wav")
    generic_notification_3         = _path_to(_p, _a, "GenericNotification3.wav")
    generic_notification_4         = _path_to(_p, _a, "GenericNotification4.wav")
    generic_notification_5         = _path_to(_p, _a, "GenericNotification5.wav")
    generic_notification_6         = _path_to(_p, _a, "GenericNotification6.wav")
    generic_notification_7         = _path_to(_p, _a, "GenericNotification7.wav")
    generic_notification_8         = _path_to(_p, _a, "GenericNotification8.wav")
    generic_notification_9         = _path_to(_p, _a, "GenericNotification9.wav")
    generic_notification_10a       = _path_to(_p, _a, "GenericNotification10a.wav")
    generic_notification_10b       = _path_to(_p, _a, "GenericNotification10b.wav")
    generic_notification_11        = _path_to(_p, _a, "GenericNotification11.wav")
    handle_drag_tick               = _path_to(_p, _a, "HandleDragTick.wav")
    little_noise                   = _path_to(_p, _a, "LittleNoise.wav")
    little_swoosh_1a               = _path_to(_p, _a, "LittleSwoosh1a.wav")
    little_swoosh_1b               = _path_to(_p, _a, "LittleSwoosh1b.wav")
    little_swoosh_2a               = _path_to(_p, _a, "LittleSwoosh2a.wav")
    little_swoosh_2b               = _path_to(_p, _a, "LittleSwoosh2b.wav")
    little_swoosh_3                = _path_to(_p, _a, "LittleSwoosh3.wav")
    little_swoosh_4                = _path_to(_p, _a, "LittleSwoosh4.wav")
    little_swoosh_5                = _path_to(_p, _a, "LittleSwoosh5.wav")
    maximize_1                     = _path_to(_p, _a, "Maximize1.wav")
    maximize_2                     = _path_to(_p, _a, "Maximize2.wav")
    maximize_3                     = _path_to(_p, _a, "Maximize3.wav")
    maximize_4                     = _path_to(_p, _a, "Maximize4.wav")
    minimize_1                     = _path_to(_p, _a, "Minimize1.wav")
    minimize_2                     = _path_to(_p, _a, "Minimize2.wav")
    minimize_3                     = _path_to(_p, _a, "Minimize3.wav")
    minimize_4                     = _path_to(_p, _a, "Minimize4.wav")
    open_or_enable_1               = _path_to(_p, _a, "OpenOrEnable1.wav")
    open_or_enable_2               = _path_to(_p, _a, "OpenOrEnable2.wav")
    open_or_enable_3               = _path_to(_p, _a, "OpenOrEnable3.wav")
    open_or_enable_4a              = _path_to(_p, _a, "OpenOrEnable4a.wav")
    open_or_enable_4b              = _path_to(_p, _a, "OpenOrEnable4b.wav")
    open_or_enable_5               = _path_to(_p, _a, "OpenOrEnable5.wav")
    popup_1                        = _path_to(_p, _a, "Popup1.wav")
    popup_2                        = _path_to(_p, _a, "Popup2.wav")
    popup_3                        = _path_to(_p, _a, "Popup3.wav")
    popup_4a                       = _path_to(_p, _a, "Popup4a.wav")
    popup_4b                       = _path_to(_p, _a, "Popup4b.wav")
    sci_fi_notification_1          = _path_to(_p, _a, "SciFiNotification1.wav")
    sci_fi_notification_2          = _path_to(_p, _a, "SciFiNotification2.wav")
    sci_fi_notification_3          = _path_to(_p, _a, "SciFiNotification3.wav")
    snappy_button_1                = _path_to(_p, _a, "SnappyButton1.wav")
    snappy_button_2                = _path_to(_p, _a, "SnappyButton2.wav")
    snappy_button_3                = _path_to(_p, _a, "SnappyButton3.wav")
    snappy_button_4                = _path_to(_p, _a, "SnappyButton4.wav")
    snappy_button_5                = _path_to(_p, _a, "SnappyButton5.wav")
    success_1                      = _path_to(_p, _a, "Success1.wav")
    success_2                      = _path_to(_p, _a, "Success2.wav")
    success_3                      = _path_to(_p, _a, "Success3.wav")
    success_4                      = _path_to(_p, _a, "Success4.wav")
    success_5                      = _path_to(_p, _a, "Success5.wav")
    success_6                      = _path_to(_p, _a, "Success6.wav")
    success_7a                     = _path_to(_p, _a, "Success7a.wav")
    success_7b                     = _path_to(_p, _a, "Success7b.wav")
    success_9                      = _path_to(_p, _a, "Success9.wav")
    success_10                     = _path_to(_p, _a, "Success10.wav")
    success_11                     = _path_to(_p, _a, "Success11.wav")
    success_12a                    = _path_to(_p, _a, "Success12a.wav")
    success_12b                    = _path_to(_p, _a, "Success12b.wav")
    success_13                     = _path_to(_p, _a, "Success13.wav")
    swoosh_slide_1a                = _path_to(_p, _a, "SwooshSlide1a.wav")
    swoosh_slide_1b                = _path_to(_p, _a, "SwooshSlide1b.wav")
    swoosh_slide_2                 = _path_to(_p, _a, "SwooshSlide2.wav")
    swoosh_slide_3                 = _path_to(_p, _a, "SwooshSlide3.wav")
    swoosh_slide_4                 = _path_to(_p, _a, "SwooshSlide4.wav")
    swoosh_slide_5                 = _path_to(_p, _a, "SwooshSlide5.wav")

    @staticmethod
    def all_containing(include_text, exclude_text=()):
        return frozenset([p for p in ModernUI._a if (include_text in p and not any(e in p for e in exclude_text))])

    @staticmethod
    def _assets_to_code():
        """Utility method that gen's the above boilerplate code (not used at runtime).
        """

        file_to_process = "/home/david/Coding/python/circuits/assets/sounds/Cyberleaf-ModernUISFX/manifest.txt"

        with open(file_to_process) as f:
            lines = f.readlines()
            lines = [line.rstrip() for line in lines]

        tabs = 8

        for l in lines:
            refname = camel_to_snake(l.replace(".wav", ""))
            if len(refname) < tabs * 4 - 2:
                refname += (" " * ((tabs * 4 - 2) - len(refname)))
            print(f"{refname} = _path_to(_p, _a, \"{l}\")")


MENU_BLIP = ModernUI.clicky_button_3a
MENU_ACCEPT = ModernUI.clicky_button_3b
MENU_ERROR = ModernUI.error_1
MENU_BACK = ModernUI.clicky_button_10b
MENU_START = ModernUI.open_or_enable_4a
MENU_SLIDE = ModernUI.little_swoosh_3

LEVEL_START = ModernUI.open_or_enable_4b
LEVEL_QUIT = ModernUI.close_or_disable_4
LEVEL_FAILED = ModernUI.error_5

BLOCK_BREAK = ModernUI.clicky_button_1b
BLOCK_PRIMED_TO_FALL = ModernUI.clicky_button_2
SWITCH_ACTIVATED = ModernUI.clicky_button_9a   # TODO different sounds for different colored switches?
SWITCH_DEACTIVATED = ModernUI.clicky_button_9b
TELEPORT = ModernUI.all_containing("Success")

PLAYER_JUMP = ModernUI.all_containing("GenericButton")
PLAYER_DIALOG = ModernUI.little_noise
PLAYER_DEATH = ModernUI.all_containing("Error", exclude_text=("5",))
PLAYER_ALERT = ModernUI._a
PLAYER_PICKUP = ModernUI.all_containing("ClickyButton")
PLAYER_PUTDOWN = ModernUI.all_containing("ClickyButton")
PLAYER_FLY = ModernUI.all_containing("Popup")


if __name__ == "__main__":
    ModernUI._assets_to_code()
