import 'package:flutter_test/flutter_test.dart';

import 'package:sentineleye/shared/models/camera.dart';

void main() {
  test('Camera deserializes from JSON', () {
    final c = Camera.fromJson({
      'id': '1',
      'name': 'Front Door',
      'location': 'Outside',
      'protocol': 'rtsp',
      'url': 'rtsp://x',
      'enabled': true,
      'status': 'online',
      'target_fps': 15,
    });
    expect(c.name, 'Front Door');
    expect(c.protocol, 'rtsp');
    expect(c.enabled, true);
  });
}
