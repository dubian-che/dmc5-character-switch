from pathlib import Path

SOURCE = Path('outputs/DMC5CharacterSwitch')


def install_module_loader(lua):
    """Load the real shared runtime while testing modules outside the game."""
    lua.globals().dofile = lambda path: lua.execute((SOURCE / Path(path).name).read_text())


def install_input_profile_helper(lua):
    """Use the real profile transaction in narrow core fixtures as well."""
    lua.execute('''
    savedFindType=sdk.find_type_definition;savedHook=sdk.hook
    sdk.hook=function()end
    sdk.find_type_definition=function(n)
      if n=='app.PlayerManager'then return {get_method=function()return {}end}end
      return savedFindType(n)
    end
    ''')
    runtime=lua.execute((SOURCE / 'dmc5_switch_runtime.lua').read_text())
    lua.globals().realInputProfile=runtime.withInputProfile
    lua.globals().realControlProfile=runtime.withControlProfile
    lua.globals().realSelectManual=runtime.selectManual
    lua.execute('sdk.find_type_definition=savedFindType;sdk.hook=savedHook')

