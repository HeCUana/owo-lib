package io.wispforest.owo.samples.braid;

import io.wispforest.owo.braid.core.BraidScreen;
import io.wispforest.owo.braid.core.BraidScreenSettings;
import io.wispforest.owo.braid.core.Insets;
import io.wispforest.owo.braid.framework.BuildContext;
import io.wispforest.owo.braid.framework.proxy.WidgetState;
import io.wispforest.owo.braid.framework.widget.StatefulWidget;
import io.wispforest.owo.braid.framework.widget.Widget;
import io.wispforest.owo.braid.widgets.Navigator;
import io.wispforest.owo.braid.widgets.basic.Center;
import io.wispforest.owo.braid.widgets.basic.IntrinsicWidth;
import io.wispforest.owo.braid.widgets.basic.Padding;
import io.wispforest.owo.braid.widgets.basic.Panel;
import io.wispforest.owo.braid.widgets.button.MessageButton;
import io.wispforest.owo.braid.widgets.flex.Column;
import io.wispforest.owo.braid.widgets.flex.CrossAxisAlignment;
import io.wispforest.owo.braid.widgets.flex.MainAxisAlignment;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

import java.util.List;

/**
 * Client-only half of {@link BraidSamplesItem}.
 *
 * <p>Everything that touches {@code BraidScreen} / {@code Minecraft} lives here so that
 * {@code BraidSamplesItem} stays loadable on a dedicated server. Referencing a client-only type
 * from a field or from the class's static initializer makes the JVM resolve that class while the
 * item class is initialized, which fails on a server with
 * {@code Cannot load class net.minecraft.client.gui.screens.Screen in environment type SERVER}.
 */
@Environment(EnvType.CLIENT)
public final class BraidSamplesClient {

    private BraidSamplesClient() {}

    public static void open() {
        Minecraft.getInstance().gui.setScreen(new BraidScreen(screenSettings(), new SampleSelector()));
    }

    // NOTE: a static field of a client type would defeat the purpose of this class existing,
    // so the settings are built on demand instead.
    private static BraidScreenSettings screenSettings() {
        var settings = new BraidScreenSettings();
        settings.shouldPause = false;

        return settings;
    }

    private static List<Sample> allSamples() {
        return List.of(
            new Sample(new SimpleCounter(), "Simple Counter"),
            new Sample(new SharedCounter(), "Shared Counter"),
            new Sample(new LayoutWidgetExamples(), "Layout Widget Examples")
        );
    }

    public record Sample(Widget widget, String name) {}

    public static class SampleSelector extends StatefulWidget {
        @Override
        public WidgetState<SampleSelector> createState() {
            return new State();
        }

        public static class State extends WidgetState<SampleSelector> {

            @Override
            public Widget build(BuildContext context) {
                return new Center(
                    new Panel(
                        Panel.VANILLA_LIGHT,
                        new Padding(
                            Insets.all(6),
                            new Panel(
                                Panel.VANILLA_INSET,
                                new Padding(
                                    Insets.all(4),
                                    new IntrinsicWidth(
                                        new Column(
                                            MainAxisAlignment.CENTER,
                                            CrossAxisAlignment.CENTER,
                                            new Padding(Insets.vertical(2)),
                                            allSamples().stream()
                                                .map(sample -> new MessageButton(
                                                    Component.literal(sample.name()),
                                                    () -> Navigator.push(context, sample.widget())
                                                ))
                                                .toList()
                                        )
                                    )
                                )
                            )
                        )
                    )
                );
            }
        }
    }
}
