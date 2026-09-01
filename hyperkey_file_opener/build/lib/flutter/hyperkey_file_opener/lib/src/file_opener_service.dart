import 'package:flet/flet.dart';
import 'package:open_filex/open_filex.dart';

class HyperkeyFileOpenerService extends FletService {
  HyperkeyFileOpenerService({required super.control});

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_invokeMethod);
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    if (name != 'open_file') {
      throw Exception('Unknown HyperkeyFileOpener method: $name');
    }

    final map = Map<String, dynamic>.from(args as Map);
    final path = map['path']?.toString();
    final mimeType = map['mime_type']?.toString();

    if (path == null || path.trim().isEmpty) {
      throw Exception('No file path was provided.');
    }

    final result = await OpenFilex.open(
      path,
      type: (mimeType == null || mimeType.isEmpty) ? null : mimeType,
    );

    return {
      'result_type': result.type.toString(),
      'message': result.message,
    };
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_invokeMethod);
    super.dispose();
  }
}
