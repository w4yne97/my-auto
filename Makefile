.PHONY: backup-shares

backup-shares:
	rsync -av --delete shares/ ~/.local/share/auto/reading/shares-archive/
