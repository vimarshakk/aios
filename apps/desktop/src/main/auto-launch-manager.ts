/**
 * AutoLaunchManager — Start app on system login.
 */

import { app } from "electron";

export class AutoLaunchManager {
  private enabled: boolean;

  constructor() {
    this.enabled = app.getLoginItemSettings().openAtLogin;
  }

  isEnabled(): boolean {
    this.enabled = app.getLoginItemSettings().openAtLogin;
    return this.enabled;
  }

  setEnabled(enabled: boolean): void {
    app.setLoginItemSettings({
      openAtLogin: enabled,
      name: "AIOS",
    });
    this.enabled = enabled;
  }

  toggle(): boolean {
    this.setEnabled(!this.isEnabled());
    return this.isEnabled();
  }
}

export default AutoLaunchManager;
