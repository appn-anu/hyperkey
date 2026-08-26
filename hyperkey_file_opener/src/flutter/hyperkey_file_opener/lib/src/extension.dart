import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';

import 'file_opener_service.dart';

class Extension extends FletExtension {
  @override
  void ensureInitialized() {}

  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case 'HyperkeyFileOpener':
        return HyperkeyFileOpenerService(control: control);
      default:
        return null;
    }
  }

  @override
  Widget? createWidget(Key? key, Control control) => null;
}
