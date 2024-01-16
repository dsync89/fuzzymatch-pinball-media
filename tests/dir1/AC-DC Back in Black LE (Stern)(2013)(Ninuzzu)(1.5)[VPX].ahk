; Get the full path of the script
scriptFullPath := A_ScriptFullPath
scriptDirectory := StrReplace(scriptFullPath, A_ScriptName, "")
scriptFileName := SubStr(A_ScriptName, 1, StrLen(A_ScriptName) - 4) ; Remove ".ahk" extension

; Read the config.txt file
configFile := A_ScriptDir . "\" . ".config.ini"

; Read values from the config.txt file
emuPath := IniRead(configFile, "Settings", "EmuPath")
gameDbPath := IniRead(configFile, "Settings", "GameDbPath")
romDir := IniRead(configFile, "RomPath", "RomDir")
visualPinballLibraryDir := IniRead(configFile, "Settings", "VisualPinballLibraryPath")
startFullScreen := IniRead(configFile, "Settings", "StartFullScreen")
debug := IniRead(configFile, "Settings", "Debug")

root := romDir

CT := ""
CD := ""
HD := ""
FD := ""


FindMusicFiles(path) {
	musicFilesArr := Array() ; store all the .fpl file found

	pathToFind := path "\*.mp3"
	pathToFindOgg := path "\*.ogg"
	if debug
		MsgBox Format("Finding .mp3 in {1}", path)

	Loop Files, pathToFind, "R" {
		if debug
			MsgBox Format("Putting .mp3 file: {1} to the list", A_LoopFilePath)
		musicFilesArr.Push A_LoopFilePath
	}

	if debug
		MsgBox Format("Finding .ogg in {1}", pathToFindOgg)

	Loop Files, pathToFindOgg, "R" {
		if debug
			MsgBox Format("Putting .ogg file: {1} to the list", A_LoopFilePath)
		musicFilesArr.Push A_LoopFilePath
	}

	return musicFilesArr
}

; CopyMusicFilesToVisualPinballLibrary(musicFilesArr, visualPinballLibraryDir) {
; 	Loop(musicFilesArr.Length) {
; 		; check if .fpl already exist in FuturePinball Library folder, skip if already exist
; 		SplitPath musicFilesArr[A_Index], &name, &dir, &ext, &name_no_ext, &drive
; 		destinationFile := visualPinballLibraryDir "\" dir "\" name
; 		if debug
; 			MsgBox Format("Checking if {1} already exist in {2}", destinationFile, visualPinballLibraryDir)

; 		if FileExist(destinationFile) {
; 			if debug
; 				MsgBox Format("music file: {1} exist, skipping copy!", destinationFile)
; 		}

; 		else { ; file not exist in FP library folder, copy it
; 			if debug
; 				MsgBox Format("Copying {1} => {2}", musicFilesArr[A_Index], visualPinballLibraryDir)
; 			FileCopy musicFilesArr[A_Index], visualPinballLibraryDir, 1
; 		}
; 	}	
; }

; This will copy all music to VisualPinball\Music folder, as well as the parent
; folder to the same folder. There is no consistent music file placement in table.
; some put it to table\music and expect all music files there to be copied directly
; to Music folder. Some table put them in [table\abc] and expect the music file to use
; the abc folder name. To avoid confusion we copy them to [Music] folder, as well as the
; parent folder
CopyMusicFilesToVisualPinballLibrary(musicFilesArr, visualPinballLibraryDir) {
	Loop(musicFilesArr.Length) {
		; check if .fpl already exist in FuturePinball Library folder, skip if already exist
		SplitPath musicFilesArr[A_Index], &name, &dir, &ext, &name_no_ext, &drive
		SplitPath dir, &parentDir
		destinationFile := visualPinballLibraryDir "\" name
		destinationFolder := visualPinballLibraryDir "\" parentDir
	
		; check if the music is in a subfolder
		; if StrLower(parentDir) == "music" {
		if debug
			MsgBox Format("Checking if {1} already exist in {2}", destinationFile, visualPinballLibraryDir)

		if FileExist(destinationFile) {
			if debug
				MsgBox Format("music file: {1} exist, skipping copy!", destinationFile)
		}

		else { ; file not exist in FP library folder, copy it
			if debug
				MsgBox Format("Copying {1} => {2}", musicFilesArr[A_Index], visualPinballLibraryDir)
			FileCopy musicFilesArr[A_Index], visualPinballLibraryDir, 1
		}
	

		; Copy the whole parent folder where the music file is found
		if DirExist(destinationFolder) {
			if debug
				MsgBox Format("dir file: {1} exist, skipping copy!", destinationFolder)
		}
		else {
			if debug
				MsgBox Format("Copying {1} => {2}", dir, destinationFolder)
			DirCreate destinationFolder
			DirCopy dir, destinationFolder, 1		
		}
	}	
}


; Read each line in the game until a match is found
Contents := FileRead(gameDbPath)  ; Read the entire file into 'Contents' variable

Loop Read gameDbPath `n  ; Loop through each line (assuming newline as delimiter)
{
	Loop parse, A_LoopReadLine, A_Tab
	{
		LineText := A_LoopField
		if LineText = ""
			break

		; Split the line into parts using |
		GameInfo := StrSplit(LineText, "|")

		; Get the number of elements after splitting
		elementCount := GameInfo.Length

		gameTitle := Trim(GameInfo[1])

		; Check if the AHK script's filename matches the GameTitle
		if (gameTitle = scriptFileName)
		{
			pinballTableArr := Array()

			bootNotes := ""

			Loop(GameInfo.Length) {
				if (A_Index > 1)
				{
					_bootSource := Trim(GameInfo[A_Index])					

					if InStr(_bootSource, ".vpx") {
						FD := Chr(34) . root . "\" . gameTitle . "\" . _bootSource . Chr(34)
						pinballTableArr.Push FD
					}  					

					if InStr(_bootSource, "Notes:") {
						bootNotes := _bootSource
					} 					
				}
			}    

			; Print detected boot media
			; Loop pinballTableArr.Length {
			; 	if debug 
			; 		MsgBox Format("FD{1}: {2}", A_Index-1, pinballTableArr[A_Index])
			; }							

			; =============================================================================================
			; Find .fpl files and import to Future Pinball\Library folder
			; Since there is no standard way to put the .fpl files, a table might have its .fpl files in
			; - [table]\lib.fpl
			; - [table]\[Library]\lib.fpl
			; - [table]\[1.0]\lib.fpl
			; - [table]\[1.0]\[night mod]\lib.fpl
			; * [...] is a folder
			
			; This script will try to first import  all .fpl it could find in [table] folder.
			; Then it will find .fpl in a specific folder where the .fpt is booted from, which could be nested below [table] folder.
			; The .fpl from the specific folder will override any .fpl found earlier in its parent [table] folder, because some table like: 
			; [Tales of the Arabian Nights (Williams)(1996)(smoke)(1.5)[FP Physics Adjustment 2.7][BAM_v1.4-240 minimum]] 
			; has the same .fpl file named in all version folders below its parent [table folder], and they all use the same name.
			; e.g. [table]\[1.0]\lib.fpt
			; e.g. [table]\[1.1]\lib.fpt
			; So we want to make sure that the .fpl is from the specific ones where .fpt is located
			; =============================================================================================
			scriptFolderFullpath := scriptDirectory "\" scriptFileName

			; first, find all .fpl files globally in the parent game folder
			musicFilesArr := FindMusicFiles(scriptFolderFullpath)

			; lastly, find it in the game specific folder where .fpt is located, if any
			SplitPath pinballTableArr[1], &name, &dir, &ext, &name_no_ext, &drive
			musicFolderFullpath := StrReplace(dir, Chr(34), "")

			; musicFilesInGameSubdir := FindMusicFiles(scriptFolderFullpath) 
			; Loop musicFilesInGameSubdir {
			; 	fplFilesArr.Push musicFilesInGameSubdir[A_Index]
			; }	

			; Finally copy the music file
			CopyMusicFilesToVisualPinballLibrary(musicFilesArr, visualPinballLibraryDir)
		
			; =============================================================================================
			; Run DmdExt
			; =============================================================================================
			; DmdExtCommand := Chr(34) futurePinballDmdExtDir Chr(34)
			; If debug
			; 	MsgBox Format("Command: {1}", DmdExtCommand)			
			; Run(DmdExtCommand)			
			
			; Run emulator
			bootArgs := ""
			If pinballTableArr.Length > 0 {
				Loop pinballTableArr.Length {
					bootArgs .= pinballTableArr[A_Index] . " " ; Concatenate
				}
			}

			Command := Chr(34) emuPath Chr(34) " -play " pinballTableArr[1]
			If debug
				MsgBox Format("Command: {1}", Command)
			Run(Command)


		}    
	}
}

; ============================================================
; Key Bindings
; ============================================================

Esc::
{
	ProcessClose "VPinballX.exe"
	Run "taskkill /im VPinballX.exe /F",, "Hide"

	ProcessClose "B2SBackglassServerEXE.exe"
	Run "taskkill /im B2SBackglassServerEXE.exe /F",, "Hide"

	ExitApp	
}